from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import get_db
from app.models.agent_run import AgentRun
from app.models.incident import Incident
from app.schemas.agent_run import AgentRunCreate, AgentRunResponse

router = APIRouter()

@router.get("", response_model=List[AgentRunResponse])
async def list_agent_runs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentRun).order_by(AgentRun.created_at.desc()))
    runs = result.scalars().all()
    return runs

@router.post("", response_model=AgentRunResponse, status_code=status.HTTP_201_CREATED)
async def create_agent_run(run_in: AgentRunCreate, db: AsyncSession = Depends(get_db)):
    # Verify incident exists
    inc_result = await db.execute(select(Incident).where(Incident.id == run_in.incident_id))
    if not inc_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated incident not found")

    run = AgentRun(
        incident_id=run_in.incident_id,
        status=run_in.status,
        summary=run_in.summary,
        logs=run_in.logs
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run

@router.get("/{run_id}", response_model=AgentRunResponse)
async def get_agent_run(run_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentRun).where(AgentRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AgentRun record not found")
    return run
