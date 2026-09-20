import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.observability import ProductionObservationModel
from app.services.observability.models import (
    ProductionObservationData,
    IncidentCorrelationData,
    IncidentIntelligenceReport,
    ObservabilitySeverity,
    ObservabilityStatus,
    ObservabilityProviderType,
)
from app.services.observability.providers import (
    MockObservabilityProvider,
    SentryObservabilityProvider,
    GenericWebhookProvider,
)
from app.services.observability.deduplicator import ObservabilityDeduplicator
from app.services.observability.correlator import ProductionReleaseCorrelator
from app.services.observability.security import ProductionSafetyPolicy
from app.services.brain.updater import BrainUpdater
from app.services.brain.models import BrainEvent, BrainSourceType

logger = logging.getLogger("devoncall.observability.manager")


class ObservabilityManager:
    """
    Central orchestration facade for DevOnCall Production Observability & Incident Intelligence.
    Handles webhook ingestion, signature verification, secret scrubbing, deduplication,
    release correlation, Project Brain integration, intelligence reporting, and Phase 4 handoff.
    Enforces PRODUCTION = READ_ONLY safety policy across all operations.
    """

    def __init__(self):
        self.providers = {
            "mock": MockObservabilityProvider(),
            "sentry": SentryObservabilityProvider(),
            "generic": GenericWebhookProvider(),
        }

    def get_provider(self, provider_name: str):
        name = (provider_name or "generic").lower().strip()
        return self.providers.get(name, self.providers["generic"])

    async def process_webhook(
        self,
        db: AsyncSession,
        provider_name: str,
        headers: Dict[str, str],
        payload_bytes: bytes,
        payload_dict: Dict[str, Any],
        project_id: str = "demo-project",
        secret: Optional[str] = None
    ) -> ProductionObservationModel:
        provider = self.get_provider(provider_name)

        # 1. Signature Verification
        if not provider.verify_webhook(headers, payload_bytes, secret=secret):
            logger.warning(f"Webhook signature verification failed for provider '{provider_name}'.")
            raise PermissionError(f"SECURITY_POLICY_VIOLATION: Invalid webhook signature for provider '{provider_name}'.")

        # 2. Event Normalization & Secret Scrubbing
        normalized = provider.normalize_event(payload_dict, project_id=project_id)

        # 3. Deduplication & Occurrence Increment
        observation_model, is_new = await ObservabilityDeduplicator.process_observation(db, normalized)

        # 4. Project Brain Context Event Logging
        try:
            updater = BrainUpdater()
            event_type = "PRODUCTION_INCIDENT_DETECTED" if is_new else "PRODUCTION_INCIDENT_UPDATED"
            brain_evt = BrainEvent(
                project_id=project_id,
                event_type=event_type,
                source=BrainSourceType.INCIDENT,
                source_reference=f"obs:{observation_model.id[:8]}",
                summary=f"[{observation_model.severity}] {observation_model.service} — {observation_model.message[:60]} (Occurrences: {observation_model.occurrence_count})",
                payload={
                    "observation_id": observation_model.id,
                    "fingerprint": observation_model.fingerprint,
                    "service": observation_model.service,
                    "severity": observation_model.severity,
                    "occurrence_count": observation_model.occurrence_count,
                }
            )
            await updater.record_event(db, brain_evt)
        except Exception as e:
            logger.warning(f"Could not log Project Brain observation event: {e}")

        return observation_model

    async def get_incident_intelligence(self, db: AsyncSession, observation_id: str) -> IncidentIntelligenceReport:
        res = await db.execute(select(ProductionObservationModel).where(ProductionObservationModel.id == observation_id))
        obs = res.scalar_one_or_none()
        if not obs:
            raise ValueError(f"Production observation '{observation_id}' not found.")

        # Correlate
        corr = await ProductionReleaseCorrelator.correlate(db, obs)

        # Build Verified Facts vs Correlations vs Hypotheses
        verified_facts = [
            f"Environment: PRODUCTION (READ_ONLY enforcement active)",
            f"Provider: {obs.provider.upper()}",
            f"Service: {obs.service}",
            f"Severity: {obs.severity}",
            f"First seen: {obs.first_seen_at.isoformat() if obs.first_seen_at else 'N/A'}, Last seen: {obs.last_seen_at.isoformat() if obs.last_seen_at else 'N/A'}",
            f"Total occurrence count: {obs.occurrence_count}",
        ]
        if obs.commit_sha:
            verified_facts.append(f"Observation release commit: {obs.commit_sha}")
        if obs.endpoint:
            verified_facts.append(f"Affected endpoint: {obs.endpoint}")

        correlations = []
        if corr.commit_found:
            correlations.append(f"Repository correlation: Matched repository snapshot files for service '{obs.service}'.")
        else:
            correlations.append("Commit correlation: Exact commit SHA unavailable in telemetry. Marked correlation confidence as UNKNOWN.")

        if corr.temporal_deployment_correlation:
            correlations.append(corr.temporal_deployment_correlation)

        if corr.historical_incidents:
            correlations.append(f"Historical correlation: Identified {len(corr.historical_incidents)} previous incidents with matching service or fingerprint.")

        if corr.project_brain_nodes:
            correlations.append(f"Project Brain correlation: Linked {len(corr.project_brain_nodes)} architectural nodes for service '{obs.service}'.")

        hypotheses = [
            f"Potential root cause in {corr.affected_files[0] if corr.affected_files else 'affected service handler'}.",
            "Error may be triggered by unhandled edge condition or null property dereference under production traffic load."
        ]

        proposed_next_steps = [
            f"Initiate Phase 4 root-cause investigation handoff for Observation #{obs.id[:8]}.",
            f"Create isolated Phase 3 workspace on branch devoncall/agent/fix-{obs.id[:6]}.",
            "Execute Phase 5 Docker sandbox validation (TEST/BUILD/TYPECHECK).",
            "Run Phase 7 Playwright browser verification against local staging preview.",
            "Deploy verified commit to Phase 9 isolated Staging environment.",
            "Request human approval before submitting Pull Request to repository default branch."
        ]

        return IncidentIntelligenceReport(
            incident_id=obs.id,
            project_id=obs.project_id,
            provider=obs.provider,
            severity=ObservabilitySeverity(obs.severity),
            status=ObservabilityStatus(obs.status),
            affected_service=obs.service,
            affected_endpoint=obs.endpoint,
            release=obs.release,
            commit_sha=obs.commit_sha,
            message=obs.message,
            verified_facts=verified_facts,
            correlations=correlations,
            hypotheses=hypotheses,
            project_brain_context=corr.project_brain_nodes,
            historical_incidents=corr.historical_incidents,
            likely_files=corr.affected_files,
            investigation_context={
                "fingerprint": obs.fingerprint,
                "stack_trace": obs.stack_trace,
                "occurrence_count": obs.occurrence_count,
            },
            proposed_next_steps=proposed_next_steps,
            confidence_score=0.88 if corr.commit_found else 0.65
        )

    async def update_status(self, db: AsyncSession, observation_id: str, new_status: ObservabilityStatus) -> ProductionObservationModel:
        res = await db.execute(select(ProductionObservationModel).where(ProductionObservationModel.id == observation_id))
        obs = res.scalar_one_or_none()
        if not obs:
            raise ValueError(f"Production observation '{observation_id}' not found.")

        # Update metadata status only — NEVER execute production operations!
        is_ok, reason = ProductionSafetyPolicy.validate_action("UPDATE_INCIDENT_STATUS", environment="PRODUCTION")
        if not is_ok:
            raise PermissionError(reason)

        obs.status = new_status.value if hasattr(new_status, 'value') else new_status
        await db.commit()
        await db.refresh(obs)

        # Log Project Brain event
        try:
            if new_status == ObservabilityStatus.RESOLVED:
                updater = BrainUpdater()
                brain_evt = BrainEvent(
                    project_id=obs.project_id,
                    event_type="PRODUCTION_INCIDENT_RESOLVED",
                    source=BrainSourceType.INCIDENT,
                    source_reference=f"obs:{obs.id[:8]}",
                    summary=f"Incident #{obs.id[:8]} status marked as RESOLVED.",
                    payload={"observation_id": obs.id, "status": "RESOLVED"}
                )
                await updater.record_event(db, brain_evt)
        except Exception as e:
            logger.warning(f"Could not log Project Brain status change event: {e}")

        return obs

    async def handoff_to_phase4_investigation(self, db: AsyncSession, observation_id: str) -> Dict[str, Any]:
        """
        Hands off production observation to Phase 4 investigation pipeline.
        Creates or links an Incident model record and triggers workspace investigation context.
        """
        res = await db.execute(select(ProductionObservationModel).where(ProductionObservationModel.id == observation_id))
        obs = res.scalar_one_or_none()
        if not obs:
            raise ValueError(f"Production observation '{observation_id}' not found.")

        obs.status = "INVESTIGATING"
        await db.commit()

        # Link to Phase 4 Incident model if needed
        from app.models.incident import Incident
        inc_stmt = select(Incident).where(Incident.id == obs.id)
        inc_res = await db.execute(inc_stmt)
        existing_inc = inc_res.scalar_one_or_none()

        if not existing_inc:
            new_inc = Incident(
                id=obs.id,
                project_id=obs.project_id,
                external_event_id=obs.external_event_id,
                title=obs.message,
                status="INVESTIGATING",
                severity=obs.severity,
                environment="PRODUCTION",
                culprit=obs.service,
                occurrence_count=obs.occurrence_count,
                normalized_metadata=obs.metadata_payload
            )
            db.add(new_inc)
            await db.commit()

        return {
            "status": "HANDOFF_SUCCESS",
            "observation_id": obs.id,
            "incident_id": obs.id,
            "project_id": obs.project_id,
            "target_branch": f"devoncall/agent/fix-{obs.id[:6]}",
            "next_phase": "PHASE_4_ROOT_CAUSE_INVESTIGATION"
        }
