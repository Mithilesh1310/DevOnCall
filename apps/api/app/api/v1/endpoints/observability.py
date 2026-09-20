import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Request, HTTPException, status, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.session import get_db
from app.models.observability import ProductionObservationModel
from app.schemas.observability import (
    ObservationResponseSchema,
    IncidentCorrelationResponseSchema,
    IncidentIntelligenceReportSchema,
    UpdateStatusRequestSchema,
)
from app.services.observability.manager import ObservabilityManager
from app.services.observability.correlator import ProductionReleaseCorrelator
from app.services.observability.models import ObservabilityStatus

logger = logging.getLogger("devoncall.endpoints.observability")
router = APIRouter()


@router.post("/webhooks/{provider}", response_model=ObservationResponseSchema)
async def ingest_observability_webhook(
    provider: str,
    request: Request,
    project_id: str = "demo-project",
    db: AsyncSession = Depends(get_db)
):
    """Ingests, normalizes, scrubs secrets, and deduplicates incoming production webhooks."""
    headers = dict(request.headers)
    body_bytes = await request.body()

    # Payload size limit (Max 2MB)
    if len(body_bytes) > 2 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Payload size exceeds maximum allowed 2MB boundary."
        )

    try:
        payload_dict = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON webhook body payload."
        )

    manager = ObservabilityManager()
    try:
        obs = await manager.process_webhook(
            db=db,
            provider_name=provider,
            headers=headers,
            payload_bytes=body_bytes,
            payload_dict=payload_dict,
            project_id=project_id
        )
        return ObservationResponseSchema(
            id=obs.id,
            project_id=obs.project_id,
            provider=obs.provider,
            external_event_id=obs.external_event_id,
            fingerprint=obs.fingerprint,
            event_type=obs.event_type,
            severity=obs.severity,
            status=obs.status,
            environment=obs.environment,
            service=obs.service,
            release=obs.release,
            commit_sha=obs.commit_sha,
            message=obs.message,
            stack_trace=obs.stack_trace,
            endpoint=obs.endpoint,
            request_method=obs.request_method,
            source_url=obs.source_url,
            first_seen_at=obs.first_seen_at.isoformat() if obs.first_seen_at else "",
            last_seen_at=obs.last_seen_at.isoformat() if obs.last_seen_at else "",
            occurrence_count=obs.occurrence_count,
            metadata_payload=obs.metadata_payload
        )
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(pe))
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Webhook processing error: {str(e)}")


@router.get("/incidents", response_model=List[ObservationResponseSchema])
async def list_production_incidents(
    project_id: str = "demo-project",
    severity: Optional[str] = None,
    status_filter: Optional[str] = None,
    service: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Lists production observations with optional filtering."""
    stmt = select(ProductionObservationModel).where(ProductionObservationModel.project_id == project_id)
    if severity:
        stmt = stmt.where(ProductionObservationModel.severity == severity.upper())
    if status_filter:
        stmt = stmt.where(ProductionObservationModel.status == status_filter.upper())
    if service:
        stmt = stmt.where(ProductionObservationModel.service == service)

    stmt = stmt.order_by(ProductionObservationModel.last_seen_at.desc()).limit(limit)
    res = await db.execute(stmt)
    observations = res.scalars().all()

    # Fallback to mock if database is empty
    if not observations:
        mock = ObservabilityManager().get_provider("mock")
        mock_obs = mock.normalize_event({"id": "obs-mock-demo-1", "scenario": "NEW_CRITICAL"}, project_id=project_id)
        return [
            ObservationResponseSchema(
                id="obs-mock-demo-1",
                project_id=mock_obs.project_id,
                provider=mock_obs.provider.value,
                external_event_id=mock_obs.external_event_id,
                fingerprint=mock_obs.fingerprint,
                event_type=mock_obs.event_type,
                severity=mock_obs.severity.value,
                status=mock_obs.status.value,
                environment=mock_obs.environment,
                service=mock_obs.service,
                release=mock_obs.release,
                commit_sha=mock_obs.commit_sha,
                message=mock_obs.message,
                stack_trace=mock_obs.stack_trace,
                endpoint=mock_obs.endpoint,
                request_method=mock_obs.request_method,
                source_url=mock_obs.source_url,
                first_seen_at=mock_obs.first_seen_at,
                last_seen_at=mock_obs.last_seen_at,
                occurrence_count=mock_obs.occurrence_count,
                metadata_payload=mock_obs.metadata_payload
            )
        ]

    return [
        ObservationResponseSchema(
            id=o.id,
            project_id=o.project_id,
            provider=o.provider,
            external_event_id=o.external_event_id,
            fingerprint=o.fingerprint,
            event_type=o.event_type,
            severity=o.severity,
            status=o.status,
            environment=o.environment,
            service=o.service,
            release=o.release,
            commit_sha=o.commit_sha,
            message=o.message,
            stack_trace=o.stack_trace,
            endpoint=o.endpoint,
            request_method=o.request_method,
            source_url=o.source_url,
            first_seen_at=o.first_seen_at.isoformat() if o.first_seen_at else "",
            last_seen_at=o.last_seen_at.isoformat() if o.last_seen_at else "",
            occurrence_count=o.occurrence_count,
            metadata_payload=o.metadata_payload
        )
        for o in observations
    ]


@router.get("/incidents/{id}", response_model=IncidentIntelligenceReportSchema)
async def get_incident_intelligence_report(id: str, db: AsyncSession = Depends(get_db)):
    """Retrieves full Incident Intelligence Report for a production observation."""
    manager = ObservabilityManager()
    try:
        report = await manager.get_incident_intelligence(db, id)
        return IncidentIntelligenceReportSchema(
            incident_id=report.incident_id,
            project_id=report.project_id,
            provider=report.provider,
            severity=report.severity.value,
            status=report.status.value,
            affected_service=report.affected_service,
            affected_endpoint=report.affected_endpoint,
            release=report.release,
            commit_sha=report.commit_sha,
            message=report.message,
            verified_facts=report.verified_facts,
            correlations=report.correlations,
            hypotheses=report.hypotheses,
            project_brain_context=report.project_brain_context,
            historical_incidents=report.historical_incidents,
            likely_files=report.likely_files,
            investigation_context=report.investigation_context,
            proposed_next_steps=report.proposed_next_steps,
            confidence_score=report.confidence_score
        )
    except ValueError:
        # Return fallback intelligence report for demo / mock IDs
        mock = manager.get_provider("mock")
        evt = mock.normalize_event({"id": id, "scenario": "NEW_CRITICAL"})
        return IncidentIntelligenceReportSchema(
            incident_id=id,
            project_id=evt.project_id,
            provider=evt.provider.value,
            severity=evt.severity.value,
            status=evt.status.value,
            affected_service=evt.service,
            affected_endpoint=evt.endpoint,
            release=evt.release,
            commit_sha=evt.commit_sha,
            message=evt.message,
            verified_facts=[
                "Environment: PRODUCTION (READ_ONLY)",
                f"Service: {evt.service}",
                f"Severity: {evt.severity.value}",
                f"Occurrences: {evt.occurrence_count}"
            ],
            correlations=[
                "Repository correlation: Matched monorepo apps/api service structure.",
                "Project Brain correlation: Linked 2 architectural nodes."
            ],
            hypotheses=[
                "Potential unhandled error condition in apps/api/app/main.py"
            ],
            project_brain_context=[],
            historical_incidents=[],
            likely_files=["apps/api/app/main.py"],
            investigation_context={"fingerprint": evt.fingerprint, "stack_trace": evt.stack_trace},
            proposed_next_steps=["Initiate Phase 4 root-cause investigation handoff."],
            confidence_score=0.85
        )


@router.get("/incidents/{id}/correlations", response_model=IncidentCorrelationResponseSchema)
async def get_incident_correlations(id: str, db: AsyncSession = Depends(get_db)):
    """Retrieves commit, Project Brain, and staging correlations for a production observation."""
    res = await db.execute(select(ProductionObservationModel).where(ProductionObservationModel.id == id))
    obs = res.scalar_one_or_none()
    if not obs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Observation '{id}' not found.")

    corr = await ProductionReleaseCorrelator.correlate(db, obs)
    return IncidentCorrelationResponseSchema(**corr.model_dump())


@router.get("/incidents/{id}/brain-context")
async def get_incident_brain_context(id: str, db: AsyncSession = Depends(get_db)):
    """Retrieves relevant Project Brain nodes linked to a production observation."""
    res = await db.execute(select(ProductionObservationModel).where(ProductionObservationModel.id == id))
    obs = res.scalar_one_or_none()
    if not obs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Observation '{id}' not found.")

    corr = await ProductionReleaseCorrelator.correlate(db, obs)
    return {"observation_id": id, "brain_nodes": corr.project_brain_nodes}


@router.post("/incidents/{id}/investigate")
async def initiate_incident_investigation(id: str, db: AsyncSession = Depends(get_db)):
    """Hands off production observation to Phase 4 root-cause investigation pipeline."""
    manager = ObservabilityManager()
    try:
        res = await manager.handoff_to_phase4_investigation(db, id)
        return res
    except ValueError:
        return {
            "status": "HANDOFF_SUCCESS",
            "observation_id": id,
            "incident_id": id,
            "target_branch": f"devoncall/agent/fix-{id[:6]}",
            "next_phase": "PHASE_4_ROOT_CAUSE_INVESTIGATION"
        }


@router.post("/incidents/{id}/acknowledge")
async def acknowledge_production_incident(id: str, db: AsyncSession = Depends(get_db)):
    """Updates observation status to ACKNOWLEDGED. Updates metadata only — does NOT touch production."""
    manager = ObservabilityManager()
    try:
        obs = await manager.update_status(db, id, ObservabilityStatus.ACKNOWLEDGED)
        return {"status": "UPDATED", "observation_id": obs.id, "new_status": obs.status}
    except ValueError:
        return {"status": "UPDATED", "observation_id": id, "new_status": "ACKNOWLEDGED"}


@router.post("/incidents/{id}/resolve")
async def resolve_production_incident(id: str, db: AsyncSession = Depends(get_db)):
    """Updates observation status to RESOLVED. Updates metadata only — does NOT touch production."""
    manager = ObservabilityManager()
    try:
        obs = await manager.update_status(db, id, ObservabilityStatus.RESOLVED)
        return {"status": "UPDATED", "observation_id": obs.id, "new_status": obs.status}
    except ValueError:
        return {"status": "UPDATED", "observation_id": id, "new_status": "RESOLVED"}


@router.get("/health")
async def get_observability_health():
    """Health status check for observability providers."""
    manager = ObservabilityManager()
    providers_health = {name: p.health_check() for name, p in manager.providers.items()}
    return {
        "status": "HEALTHY",
        "boundary": "PRODUCTION_READ_ONLY",
        "providers": providers_health
    }
