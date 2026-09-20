import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Header, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import get_db
from app.models.project import Project
from app.models.incident import Incident
from app.services.integrations.sentry import (
    verify_sentry_signature, SentryNormalizer, MockSentryProvider, SentryIncident
)

logger = logging.getLogger("devoncall.webhooks.sentry")
router = APIRouter()

@router.post("/sentry")
async def handle_sentry_webhook(
    request: Request,
    sentry_hook_signature: str | None = Header(None, alias="sentry-hook-signature"),
    db: AsyncSession = Depends(get_db)
):
    raw_body = await request.body()
    
    # 1. Verify Webhook Signature
    if not verify_sentry_signature(raw_body, sentry_hook_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Sentry webhook signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")

    # 2. Normalize Event & Redact Secrets
    normalized: SentryIncident = SentryNormalizer.normalize_event(payload, is_mock=False)

    # 3. Project / Repository Mapping
    proj_result = await db.execute(select(Project).where(
        (Project.github_repo == normalized.project_slug) | (Project.name == normalized.project_slug)
    ))
    project = proj_result.scalars().first()

    # Fallback to first project if available
    if not project:
        all_projs = await db.execute(select(Project))
        project = all_projs.scalars().first()

    if not project:
        return {
            "status": "UNMAPPED_INCIDENT",
            "message": f"Sentry project '{normalized.project_slug}' could not be correlated with any connected DevOnCall project.",
            "issue_id": normalized.issue_id,
            "event_id": normalized.event_id
        }

    # 4. Incident Deduplication (Check external_issue_id / external_event_id)
    now_utc = datetime.now(timezone.utc)
    dedup_res = await db.execute(select(Incident).where(
        (Incident.project_id == project.id) & 
        ((Incident.external_issue_id == normalized.issue_id) | (Incident.external_event_id == normalized.event_id))
    ))
    existing_incident = dedup_res.scalar_one_or_none()

    if existing_incident:
        # Update existing incident idempotently
        existing_incident.occurrence_count += 1
        existing_incident.last_seen_at = now_utc
        existing_incident.stack_trace = [f.model_dump() for f in normalized.stack_trace]
        existing_incident.error_message = normalized.error_message
        await db.commit()
        await db.refresh(existing_incident)
        
        logger.info(f"Deduplicated Sentry incident '{existing_incident.id}' (Issue: '{normalized.issue_id}', Count: {existing_incident.occurrence_count})")
        return {
            "status": "UPDATED",
            "deduplicated": True,
            "incident_id": existing_incident.id,
            "issue_id": normalized.issue_id,
            "project_id": project.id,
            "occurrence_count": existing_incident.occurrence_count
        }

    # Create new Incident record
    incident = Incident(
        project_id=project.id,
        title=f"{normalized.error_type}: {normalized.error_message[:100]}",
        status="OPEN",
        severity="HIGH",
        source="SENTRY",
        description=normalized.error_message,
        external_event_id=normalized.event_id,
        external_issue_id=normalized.issue_id,
        error_type=normalized.error_type,
        error_message=normalized.error_message,
        environment=normalized.environment,
        release=normalized.release,
        commit_sha=normalized.commit_sha,
        culprit=normalized.culprit,
        occurrence_count=normalized.occurrence_count,
        first_seen_at=now_utc,
        last_seen_at=now_utc,
        stack_trace=[f.model_dump() for f in normalized.stack_trace],
        normalized_metadata=normalized.metadata
    )
    db.add(incident)
    await db.commit()
    await db.refresh(incident)

    logger.info(f"Created new Sentry incident '{incident.id}' for issue '{normalized.issue_id}'")
    return {
        "status": "INGESTED",
        "deduplicated": False,
        "incident_id": incident.id,
        "issue_id": normalized.issue_id,
        "project_id": project.id
    }


@router.post("/sentry/simulate")
async def simulate_sentry_webhook(
    scenario: str = "javascript_type_error",
    db: AsyncSession = Depends(get_db)
):
    """
    Simulates a Sentry webhook ingestion using MockSentryProvider.
    """
    normalized: SentryIncident = MockSentryProvider.get_mock_incident(scenario)

    # Get or create demo project
    proj_result = await db.execute(select(Project))
    project = proj_result.scalars().first()

    if not project:
        project = Project(
            name="devoncall-demo",
            github_owner="devoncall",
            github_repo="demo-repo",
            default_branch="main"
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)

    now_utc = datetime.now(timezone.utc)
    
    # Check deduplication
    dedup_res = await db.execute(select(Incident).where(
        (Incident.project_id == project.id) & 
        ((Incident.external_issue_id == normalized.issue_id) | (Incident.external_event_id == normalized.event_id))
    ))
    existing = dedup_res.scalar_one_or_none()

    if existing:
        existing.occurrence_count += 1
        existing.last_seen_at = now_utc
        await db.commit()
        await db.refresh(existing)
        return {
            "status": "UPDATED",
            "deduplicated": True,
            "incident_id": existing.id,
            "issue_id": normalized.issue_id,
            "project_id": project.id,
            "occurrence_count": existing.occurrence_count
        }

    incident = Incident(
        project_id=project.id,
        title=f"{normalized.error_type}: {normalized.error_message[:100]}",
        status="OPEN",
        severity="HIGH",
        source="MOCK_SENTRY",
        description=normalized.error_message,
        external_event_id=normalized.event_id,
        external_issue_id=normalized.issue_id,
        error_type=normalized.error_type,
        error_message=normalized.error_message,
        environment=normalized.environment,
        release=normalized.release,
        commit_sha=normalized.commit_sha,
        culprit=normalized.culprit,
        occurrence_count=normalized.occurrence_count,
        first_seen_at=now_utc,
        last_seen_at=now_utc,
        stack_trace=[f.model_dump() for f in normalized.stack_trace],
        normalized_metadata=normalized.metadata
    )
    db.add(incident)
    await db.commit()
    await db.refresh(incident)

    return {
        "status": "INGESTED",
        "deduplicated": False,
        "incident_id": incident.id,
        "issue_id": normalized.issue_id,
        "project_id": project.id
    }
