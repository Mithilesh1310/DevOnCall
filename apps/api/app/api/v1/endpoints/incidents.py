from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.db.session import get_db
from app.models.incident import Incident
from app.models.incident_investigation import IncidentInvestigation
from app.models.project import Project
from app.models.agent_run import AgentRun
from app.schemas.incident import IncidentCreate, IncidentResponse, IncidentInvestigationResponse
from app.schemas.agent_run import AgentRunResponse
from app.services.incident.investigator import IncidentInvestigator, InvestigationResult
from app.services.integrations.sentry.base import SentryStackFrame
from app.services.agent import StateManager, AgentRuntime

router = APIRouter()

@router.get("", response_model=List[IncidentResponse])
async def list_incidents(
    source: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Incident).options(selectinload(Incident.investigation)).order_by(Incident.created_at.desc())
    if source:
        stmt = stmt.where(Incident.source == source)
    if status_filter:
        stmt = stmt.where(Incident.status == status_filter)

    result = await db.execute(stmt)
    incidents = result.scalars().all()
    return incidents


@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def create_incident(incident_in: IncidentCreate, db: AsyncSession = Depends(get_db)):
    proj_result = await db.execute(select(Project).where(Project.id == incident_in.project_id))
    if not proj_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated project not found")

    incident = Incident(
        project_id=incident_in.project_id,
        title=incident_in.title,
        status=incident_in.status.upper(),
        severity=incident_in.severity.upper(),
        source=incident_in.source,
        description=incident_in.description
    )
    db.add(incident)
    await db.commit()
    await db.refresh(incident)

    result = await db.execute(select(Incident).options(selectinload(Incident.investigation)).where(Incident.id == incident.id))
    return result.scalar_one()


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(incident_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Incident).options(selectinload(Incident.investigation)).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return incident


@router.post("/{incident_id}/investigate", response_model=IncidentResponse)
async def investigate_incident(incident_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Incident).options(selectinload(Incident.investigation), selectinload(Incident.project)).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    incident.status = "INVESTIGATING"
    await db.commit()

    # Reconstruct SentryStackFrame list from DB stack_trace
    sentry_frames = []
    if incident.stack_trace and isinstance(incident.stack_trace, list):
        for sf in incident.stack_trace:
            if isinstance(sf, dict):
                sentry_frames.append(SentryStackFrame(
                    file=sf.get("file", "unknown"),
                    line=sf.get("line"),
                    column=sf.get("column"),
                    function=sf.get("function"),
                    module=sf.get("module"),
                    in_app=sf.get("in_app", True),
                    raw_frame=sf.get("raw_frame")
                ))

    # Run root-cause investigator
    inv_res: InvestigationResult = await IncidentInvestigator.investigate_incident(
        incident_id=incident.id,
        project_id=incident.project_id,
        title=incident.title,
        error_type=incident.error_type or "Error",
        error_message=incident.error_message or incident.title,
        sentry_frames=sentry_frames,
        repository_snapshot=incident.project.repository_snapshot if incident.project else None
    )

    # Save or update IncidentInvestigation DB record
    if incident.investigation:
        investigation = incident.investigation
        investigation.status = inv_res.status
        investigation.confidence = inv_res.hypothesis.confidence
        investigation.hypothesis = inv_res.hypothesis.model_dump()
        investigation.evidence = inv_res.hypothesis.evidence
        investigation.relevant_files = inv_res.hypothesis.files
        investigation.relevant_stack_frames = inv_res.hypothesis.stack_frames
        investigation.repository_matches = [m.model_dump() for m in inv_res.matches]
        investigation.proposed_fix = inv_res.proposed_fix.model_dump()
        investigation.recommended_next_action = "Review Proposed Fix and trigger Phase 3 Coding Run"
    else:
        investigation = IncidentInvestigation(
            incident_id=incident.id,
            status=inv_res.status,
            confidence=inv_res.hypothesis.confidence,
            hypothesis=inv_res.hypothesis.model_dump(),
            evidence=inv_res.hypothesis.evidence,
            relevant_files=inv_res.hypothesis.files,
            relevant_stack_frames=inv_res.hypothesis.stack_frames,
            repository_matches=[m.model_dump() for m in inv_res.matches],
            proposed_fix=inv_res.proposed_fix.model_dump(),
            recommended_next_action="Review Proposed Fix and trigger Phase 3 Coding Run"
        )
        db.add(investigation)

    incident.status = "PROPOSED_FIX"
    await db.commit()
    await db.refresh(incident)

    result_fresh = await db.execute(select(Incident).options(selectinload(Incident.investigation)).where(Incident.id == incident_id))
    return result_fresh.scalar_one()


@router.post("/{incident_id}/propose-fix")
async def start_proposed_fix(incident_id: str, db: AsyncSession = Depends(get_db)):
    """
    Hands off a ProposedFix to Phase 3 AgentRuntime workflow under human approval gate.
    """
    result = await db.execute(select(Incident).options(selectinload(Incident.investigation), selectinload(Incident.project)).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    if not incident.investigation or not incident.investigation.proposed_fix:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incident has no investigation or proposed fix. Run investigation first.")

    proposed_fix = incident.investigation.proposed_fix
    task_description = f"Fix Sentry Incident: {proposed_fix.get('summary', incident.title)}"

    # 1. Create Phase 3 AgentRun DB record
    started_time = datetime.now(timezone.utc)
    agent_run = AgentRun(
        project_id=incident.project_id,
        incident_id=incident.id,
        user_task=task_description,
        status="RUNNING",
        current_goal=f"Executing fix for Sentry incident {incident.id[:8]}",
        started_at=started_time
    )
    db.add(agent_run)
    await db.commit()
    await db.refresh(agent_run)

    # 2. Initialize AgentState and execute Agent Runtime
    state = StateManager.create_initial_state(
        run_id=agent_run.id,
        project_id=incident.project_id,
        user_task=task_description,
        incident_id=incident.id
    )
    state.run_context["default_branch"] = incident.project.default_branch if incident.project else "main"

    runtime = AgentRuntime()
    final_state = await runtime.run(state, repository_snapshot=incident.project.repository_snapshot if incident.project else None)

    # 3. Update AgentRun DB record and Incident status
    from app.api.v1.endpoints.agent import _sync_state_to_run
    _sync_state_to_run(agent_run, final_state)
    
    incident.status = "AWAITING_APPROVAL"
    await db.commit()
    await db.refresh(agent_run)

    return {
        "incident_id": incident.id,
        "agent_run_id": agent_run.id,
        "status": agent_run.status,
        "proposed_fix": proposed_fix,
        "message": "Phase 3 coding workflow initiated. Awaiting human approval for PR creation."
    }


@router.post("/{incident_id}/ignore", response_model=IncidentResponse)
async def ignore_incident(incident_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Incident).options(selectinload(Incident.investigation)).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    incident.status = "IGNORED"
    await db.commit()
    await db.refresh(incident)
    return incident


@router.post("/{incident_id}/resolve", response_model=IncidentResponse)
async def resolve_incident(incident_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Incident).options(selectinload(Incident.investigation)).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    incident.status = "RESOLVED"
    await db.commit()
    await db.refresh(incident)
    return incident
