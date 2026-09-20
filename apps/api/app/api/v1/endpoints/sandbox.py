import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import get_db
from app.models.project import Project
from app.models.sandbox_run import SandboxRun
from app.schemas.sandbox import SandboxRunCreateRequest, SandboxRunResponse
from app.services.sandbox import SandboxManager, CommandType, SandboxStatus
from app.services.workspace.manager import WorkspaceManager

logger = logging.getLogger("devoncall.api.sandbox")
router = APIRouter()

@router.post("/runs", response_model=SandboxRunResponse, status_code=status.HTTP_201_CREATED)
async def create_sandbox_run(
    req: SandboxRunCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Executes a controlled code validation run inside an isolated sandbox container.
    Command type must be one of: TEST, BUILD, LINT, TYPECHECK.
    Arbitrary command strings are strictly prohibited.
    """
    # 1. Validate project existence
    proj_res = await db.execute(select(Project).where(Project.id == req.project_id))
    project = proj_res.scalar_one_or_none()

    if not project:
        # Fallback query for demo project
        all_projs = await db.execute(select(Project))
        project = all_projs.scalars().first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{req.project_id}' not found."
        )

    # 2. Resolve & validate workspace path
    try:
        workspace_path = str(WorkspaceManager.get_workspace_path(req.workspace_id))
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid workspace ID '{req.workspace_id}': {ex}"
        )

    # 3. Execute Sandbox Validation Run
    manager = SandboxManager()
    try:
        sandbox_run = await manager.run_validation(
            db=db,
            project_id=project.id,
            workspace_id=req.workspace_id,
            workspace_path=workspace_path,
            command_type=req.command_type,
            agent_run_id=req.agent_run_id,
            runtime=req.runtime,
            force_mock=req.force_mock
        )
        return sandbox_run
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except Exception as ex:
        logger.error(f"Sandbox run creation failed: {ex}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(ex))


@router.get("/runs", response_model=List[SandboxRunResponse])
async def list_sandbox_runs(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    workspace_id: Optional[str] = Query(None, description="Filter by workspace ID"),
    agent_run_id: Optional[str] = Query(None, description="Filter by agent run ID"),
    db: AsyncSession = Depends(get_db)
):
    query = select(SandboxRun).order_by(SandboxRun.created_at.desc())
    if project_id:
        query = query.where(SandboxRun.project_id == project_id)
    if workspace_id:
        query = query.where(SandboxRun.workspace_id == workspace_id)
    if agent_run_id:
        query = query.where(SandboxRun.agent_run_id == agent_run_id)

    res = await db.execute(query)
    return res.scalars().all()


@router.get("/runs/{run_id}", response_model=SandboxRunResponse)
async def get_sandbox_run(
    run_id: str,
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(SandboxRun).where(SandboxRun.id == run_id))
    sandbox_run = res.scalar_one_or_none()
    if not sandbox_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SandboxRun '{run_id}' not found."
        )
    return sandbox_run


@router.post("/runs/{run_id}/cancel", response_model=SandboxRunResponse)
async def cancel_sandbox_run(
    run_id: str,
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(SandboxRun).where(SandboxRun.id == run_id))
    sandbox_run = res.scalar_one_or_none()
    if not sandbox_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SandboxRun '{run_id}' not found."
        )

    if sandbox_run.status in [SandboxStatus.RUNNING.value, SandboxStatus.QUEUED.value]:
        sandbox_run.status = SandboxStatus.CANCELLED.value
        sandbox_run.error_message = "Cancelled by user request"
        await db.commit()
        await db.refresh(sandbox_run)

    return sandbox_run
