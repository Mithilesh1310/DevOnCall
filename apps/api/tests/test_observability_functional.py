import pytest
from httpx import AsyncClient

from app.services.observability.fingerprint import ObservabilityFingerprinter
from app.services.observability.deduplicator import ObservabilityDeduplicator
from app.services.observability.correlator import ProductionReleaseCorrelator
from app.services.observability.manager import ObservabilityManager
from app.services.observability.providers.mock_provider import MockObservabilityProvider
from app.services.observability.models import (
    ProductionObservationData,
    ObservabilitySeverity,
    ObservabilityStatus,
    ObservabilityProviderType,
)
from app.services.integrations.whatsapp.parser import WhatsAppCommandParser
from app.services.integrations.whatsapp.models import CommandType, AuthorizedDeveloper, WhatsAppRole
from app.services.integrations.whatsapp.manager import WhatsAppManager


def test_fingerprint_stability():
    """Verify fingerprints remain stable regardless of volatile timestamps or numbers."""
    fp1 = ObservabilityFingerprinter.generate_fingerprint("sentry", "error", "apps/api", "Null dereference at 2026-09-20T10:00:00 in frame 42")
    fp2 = ObservabilityFingerprinter.generate_fingerprint("sentry", "error", "apps/api", "Null dereference at 2026-09-20T15:30:00 in frame 99")

    assert fp1 == fp2


@pytest.mark.asyncio
async def test_event_deduplication_and_occurrence_increment(db_session):
    """Verify duplicate observation ingestion increments occurrence_count and updates last_seen_at."""
    obs_data = ProductionObservationData(
        project_id="test-obs-proj",
        provider=ObservabilityProviderType.GENERIC,
        external_event_id="evt-dup-101",
        fingerprint="fp-dup-1000",
        message="Database Connection Failed",
        service="apps/api",
        occurrence_count=1
    )

    # 1. Ingest first time
    m1, is_new1 = await ObservabilityDeduplicator.process_observation(db_session, obs_data)
    assert is_new1 is True
    assert m1.occurrence_count == 1

    # 2. Ingest second time with same fingerprint
    m2, is_new2 = await ObservabilityDeduplicator.process_observation(db_session, obs_data)
    assert is_new2 is False
    assert m2.id == m1.id
    assert m2.occurrence_count == 2


@pytest.mark.asyncio
async def test_release_correlation_with_commit(db_session):
    """Verify release correlation when commit SHA is provided."""
    manager = ObservabilityManager()
    obs_data = ProductionObservationData(
        project_id="corr-proj",
        provider=ObservabilityProviderType.GENERIC,
        external_event_id="evt-rel-1",
        fingerprint="fp-rel-101",
        message="Null Pointer in user lookup",
        service="apps/api",
        commit_sha="a1b2c3d4e5f6",
        release="v1.4.2"
    )

    model, _ = await ObservabilityDeduplicator.process_observation(db_session, obs_data)
    corr = await ProductionReleaseCorrelator.correlate(db_session, model)

    assert corr.commit_found is True
    assert corr.commit_sha == "a1b2c3d4e5f6"
    assert len(corr.affected_files) > 0


@pytest.mark.asyncio
async def test_release_correlation_unknown_commit(db_session):
    """Verify unknown commit SHA marks correlation confidence as UNKNOWN and NEVER invents a commit."""
    obs_data = ProductionObservationData(
        project_id="unk-proj",
        provider=ObservabilityProviderType.GENERIC,
        external_event_id="evt-unk-1",
        fingerprint="fp-unk-202",
        message="Unhandled Exception without commit info",
        service="apps/api",
        commit_sha=None,
        release=None
    )

    model, _ = await ObservabilityDeduplicator.process_observation(db_session, obs_data)
    corr = await ProductionReleaseCorrelator.correlate(db_session, model)

    assert corr.commit_found is False
    assert corr.commit_sha is None
    assert corr.correlation_confidence == "UNKNOWN"


@pytest.mark.asyncio
async def test_incident_intelligence_report_distinction(db_session):
    """Verify Incident Intelligence Report explicitly separates VERIFIED FACTS, CORRELATIONS, and HYPOTHESES."""
    manager = ObservabilityManager()
    obs_data = ProductionObservationData(
        project_id="intel-proj",
        provider=ObservabilityProviderType.MOCK,
        external_event_id="evt-intel-1",
        fingerprint="fp-intel-303",
        message="Critical Payment Gateway Timeout",
        service="apps/api",
        severity=ObservabilitySeverity.CRITICAL,
        commit_sha="a1b2c3d4e5f6"
    )

    model, _ = await ObservabilityDeduplicator.process_observation(db_session, obs_data)
    report = await manager.get_incident_intelligence(db_session, model.id)

    assert len(report.verified_facts) >= 4
    assert any("PRODUCTION" in f for f in report.verified_facts)
    assert len(report.correlations) >= 1
    assert len(report.hypotheses) >= 1
    assert len(report.proposed_next_steps) >= 3


@pytest.mark.asyncio
async def test_phase4_investigation_handoff(db_session):
    """Verify production observation handoff to Phase 4 root-cause investigation pipeline."""
    manager = ObservabilityManager()
    obs_data = ProductionObservationData(
        project_id="handoff-proj",
        provider=ObservabilityProviderType.MOCK,
        external_event_id="evt-handoff-1",
        fingerprint="fp-handoff-404",
        message="Database Pool Deadlock",
        service="apps/api"
    )

    model, _ = await ObservabilityDeduplicator.process_observation(db_session, obs_data)
    res = await manager.handoff_to_phase4_investigation(db_session, model.id)

    assert res["status"] == "HANDOFF_SUCCESS"
    assert res["observation_id"] == model.id
    assert res["next_phase"] == "PHASE_4_ROOT_CAUSE_INVESTIGATION"


def test_mock_provider_scenarios():
    """Verify MockObservabilityProvider returns correct data across all scenarios."""
    mock = MockObservabilityProvider()

    evt_crit = mock.normalize_event({"scenario": "NEW_CRITICAL"})
    assert evt_crit.severity == ObservabilitySeverity.CRITICAL

    evt_rel = mock.normalize_event({"scenario": "RELEASE_CORRELATED"})
    assert evt_rel.commit_sha == "a1b2c3d4e5f67890"

    evt_unk = mock.normalize_event({"scenario": "UNKNOWN_COMMIT"})
    assert evt_unk.commit_sha is None


def test_whatsapp_incident_commands():
    """Verify parsing and authorizing INCIDENTS CRITICAL and INCIDENTS OPEN commands."""
    cmd_crit = WhatsAppCommandParser.parse("INCIDENTS CRITICAL")
    assert cmd_crit.command_type == CommandType.INCIDENTS_CRITICAL

    cmd_open = WhatsAppCommandParser.parse("INCIDENTS OPEN")
    assert cmd_open.command_type == CommandType.INCIDENTS_OPEN

    dev = AuthorizedDeveloper(
        id="dev-obs-1",
        identity_hash="hash_obs_123",
        name="Telemetry Tester",
        phone_number_masked="+***9999",
        project_id="demo-project",
        role=WhatsAppRole.DEVELOPER,
        enabled=True
    )

    from app.services.integrations.whatsapp.policies import WhatsAppSecurityPolicy
    is_auth_crit, _ = WhatsAppSecurityPolicy.authorize_command(dev, CommandType.INCIDENTS_CRITICAL, "demo-project")
    assert is_auth_crit is True


@pytest.mark.asyncio
async def test_observability_rest_api_endpoints(client: AsyncClient):
    """Verify REST API endpoints for webhooks, incidents, intelligence reports, acknowledge, resolve, and health."""
    # 1. Webhook Ingestion Endpoint
    res_wh = await client.post(
        "/api/v1/observability/webhooks/mock",
        json={"scenario": "NEW_CRITICAL", "message": "API Test Incident"}
    )
    assert res_wh.status_code == 200
    data_wh = res_wh.json()
    obs_id = data_wh["id"]

    # 2. List Incidents Endpoint
    res_list = await client.get("/api/v1/observability/incidents?project_id=demo-project")
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1

    # 3. Incident Intelligence Report Endpoint
    res_det = await client.get(f"/api/v1/observability/incidents/{obs_id}")
    assert res_det.status_code == 200
    data_det = res_det.json()
    assert "verified_facts" in data_det
    assert "hypotheses" in data_det

    # 4. Acknowledge Endpoint (Metadata update only)
    res_ack = await client.post(f"/api/v1/observability/incidents/{obs_id}/acknowledge")
    assert res_ack.status_code == 200
    assert res_ack.json()["new_status"] == "ACKNOWLEDGED"

    # 5. Resolve Endpoint (Metadata update only)
    res_res = await client.post(f"/api/v1/observability/incidents/{obs_id}/resolve")
    assert res_res.status_code == 200
    assert res_res.json()["new_status"] == "RESOLVED"

    # 6. Health Check Endpoint
    res_h = await client.get("/api/v1/observability/health")
    assert res_h.status_code == 200
    assert res_h.json()["boundary"] == "PRODUCTION_READ_ONLY"
