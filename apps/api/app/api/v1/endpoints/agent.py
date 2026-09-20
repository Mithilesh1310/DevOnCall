import os
from typing import List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import get_db
from app.models.project import Project
from app.models.agent_run import AgentRun
from app.models.validation_attempt import ValidationAttempt
from app.models.sandbox_run import SandboxRun
from app.schemas.agent_run import CreateAgentRunRequest, AgentRunResponse, ToolCallRecordSchema, ApproveAgentRunResponse
from app.services.agent import StateManager, AgentRuntime, AgentState
from app.services.workspace import default_workspace_manager

router = APIRouter()

def _map_agent_run_response(run: AgentRun) -> AgentRunResponse:
    tool_calls: List[ToolCallRecordSchema] = []
    if run.execution_metadata and isinstance(run.execution_metadata, dict):
        raw_calls = run.execution_metadata.get("tool_calls", [])
        for c in raw_calls:
            tool_calls.append(ToolCallRecordSchema(
                tool_name=c.get("tool_name", ""),
                input_params=c.get("input_params", {}),
                success=c.get("success", False),
                summary=c.get("summary", ""),
                started_at=c.get("started_at"),
                completed_at=c.get("completed_at"),
                error=c.get("error")
            ))

    return AgentRunResponse(
        id=run.id,
        project_id=run.project_id,
        incident_id=run.incident_id,
        user_task=run.user_task,
        status=run.status,
        current_goal=run.current_goal,
        current_step=run.current_step,
        iteration_count=run.iteration_count,
        summary=run.summary,
        tool_calls=tool_calls,
        workspace_path=run.workspace_path,
        agent_branch=run.agent_branch,
        change_plan=run.change_plan,
        diff_summary=run.diff_summary,
        pull_request_url=run.pull_request_url,
        pull_request_status=run.pull_request_status,
        approved_by=run.approved_by,
        approved_at=run.approved_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_at=run.created_at
    )


def _sync_state_to_run(agent_run: AgentRun, final_state: AgentState) -> None:
    agent_run.status = final_state.status
    agent_run.current_goal = final_state.current_goal
    agent_run.current_step = final_state.current_step
    agent_run.iteration_count = final_state.iteration_count
    agent_run.summary = final_state.current_goal
    if final_state.status in ("COMPLETED", "FAILED", "CANCELLED"):
        agent_run.completed_at = datetime.now(timezone.utc)
        agent_run.finished_at = agent_run.completed_at

    # Extract workspace & PR metadata from observations
    for obs in final_state.observations:
        if obs.result and obs.result.data:
            d = obs.result.data
            if obs.tool_name == "create_workspace":
                agent_run.workspace_path = d.get("workspace_path")
                agent_run.agent_branch = d.get("branch_name")
                agent_run.base_commit_sha = d.get("base_commit_sha")
            elif obs.tool_name == "git_diff":
                agent_run.diff_summary = d
            elif obs.tool_name == "create_pull_request":
                agent_run.pull_request_url = d.get("pull_request_url") or d.get("pr_url")
                agent_run.pull_request_status = d.get("status")

    # Construct default ChangePlan if workspace edits were performed
    if agent_run.diff_summary and not agent_run.change_plan:
        files_mod = agent_run.diff_summary.get("files_changed", [])
        agent_run.change_plan = {
            "goal": f"Execute task: '{agent_run.user_task}'",
            "reason": "Modify target files in isolated workspace and submit PR",
            "files_to_modify": files_mod,
            "files_to_add": [],
            "validation_steps": ["Verify file write safety", "Check git diff", "Require human approval gate"],
            "risk_level": "LOW"
        }

    # Serialize tool calls into execution_metadata
    metadata_calls = [
        {
            "tool_name": c.tool_name,
            "input_params": c.input_params,
            "success": c.success,
            "summary": c.summary,
            "started_at": c.started_at.isoformat(),
            "completed_at": c.completed_at.isoformat(),
            "error": c.error
        }
        for c in final_state.tool_calls
    ]
    agent_run.execution_metadata = {
        "tool_calls": metadata_calls,
        "observations_count": len(final_state.observations),
        "errors": final_state.errors
    }


@router.get("/runs", response_model=List[AgentRunResponse])
async def list_agent_runs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentRun).order_by(AgentRun.created_at.desc()))
    runs = result.scalars().all()
    return [_map_agent_run_response(r) for r in runs]


@router.post("/runs", response_model=AgentRunResponse, status_code=status.HTTP_201_CREATED)
async def create_and_run_agent(
    run_req: CreateAgentRunRequest,
    db: AsyncSession = Depends(get_db)
):
    # Verify project exists
    result = await db.execute(select(Project).where(Project.id == run_req.project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{run_req.project_id}' not found")

    started_time = datetime.now(timezone.utc)

    # 1. Create AgentRun DB record
    agent_run = AgentRun(
        project_id=project.id,
        incident_id=run_req.incident_id,
        user_task=run_req.task,
        status="RUNNING",
        current_goal=f"Executing task: '{run_req.task}'",
        started_at=started_time
    )
    db.add(agent_run)
    await db.commit()
    await db.refresh(agent_run)

    # 2. Initialize AgentState
    state = StateManager.create_initial_state(
        run_id=agent_run.id,
        project_id=project.id,
        user_task=run_req.task,
        incident_id=run_req.incident_id
    )
    state.run_context["default_branch"] = project.default_branch or "main"
    state.run_context["db_session"] = db

    # 3. Execute Agent Runtime loop
    runtime = AgentRuntime()
    final_state = await runtime.run(state, repository_snapshot=project.repository_snapshot)

    # 4. Sync state to DB record
    _sync_state_to_run(agent_run, final_state)
    await db.commit()
    await db.refresh(agent_run)
    return _map_agent_run_response(agent_run)


@router.get("/runs/{run_id}", response_model=AgentRunResponse)
async def get_agent_run(run_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentRun).where(AgentRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AgentRun not found")
    return _map_agent_run_response(run)


@router.get("/runs/{run_id}/diff")
async def get_agent_run_diff(run_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentRun).where(AgentRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AgentRun not found")

    if run.diff_summary:
        return run.diff_summary

    ws_root = default_workspace_manager.get_workspace_root(run_id)
    files_changed = []
    diff_lines = []
    total_additions = 0

    if os.path.exists(ws_root):
        for root, _, files in os.walk(ws_root):
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), ws_root).replace("\\", "/")
                if not any(p in rel_path for p in [".git", ".env"]):
                    files_changed.append(rel_path)
                    try:
                        with open(os.path.join(root, file), "r", encoding="utf-8", errors="replace") as f:
                            lines = f.readlines()
                        total_additions += len(lines)
                        diff_lines.append(f"--- a/{rel_path}\n+++ b/{rel_path}\n@@ -0,0 +1,{len(lines)} @@\n" + "".join([f"+{l}" for l in lines]))
                    except Exception:
                        pass

    return {
        "files_changed": files_changed,
        "diff_text": "\n".join(diff_lines),
        "total_additions": total_additions,
        "total_deletions": 0
    }


@router.get("/runs/{run_id}/changes")
async def get_agent_run_changes(run_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentRun).where(AgentRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AgentRun not found")

    return {
        "run_id": run.id,
        "workspace_path": run.workspace_path,
        "agent_branch": run.agent_branch,
        "change_plan": run.change_plan,
        "diff_summary": run.diff_summary
    }


@router.get("/runs/{run_id}/validation")
async def get_agent_run_validation(run_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentRun).where(AgentRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AgentRun not found")

    # Fetch latest SandboxRun
    sb_res = await db.execute(
        select(SandboxRun).where(SandboxRun.agent_run_id == run_id).order_by(SandboxRun.created_at.desc())
    )
    latest_sb = sb_res.scalars().first()

    return {
        "run_id": run.id,
        "status": run.status,
        "latest_sandbox_run": latest_sb,
        "validation_summary": "Passed all target tests." if (latest_sb and latest_sb.status == "PASSED") else "Validation suite pending or required fixes."
    }


@router.get("/runs/{run_id}/validation/history")
async def get_agent_run_validation_history(run_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentRun).where(AgentRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AgentRun not found")

    sb_res = await db.execute(
        select(SandboxRun).where(SandboxRun.agent_run_id == run_id).order_by(SandboxRun.created_at.asc())
    )
    runs = sb_res.scalars().all()
    return runs


@router.post("/runs/{run_id}/continue")
async def continue_agent_run(run_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentRun).where(AgentRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AgentRun not found")

    run.status = "RUNNING"
    await db.commit()
    await db.refresh(run)
    return _map_agent_run_response(run)


@router.post("/runs/{run_id}/stop")
async def stop_agent_run(run_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentRun).where(AgentRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AgentRun not found")

    run.status = "CANCELLED"
    run.summary = "Stopped by user request."
    run.completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(run)
    return _map_agent_run_response(run)


@router.post("/runs/{run_id}/approve", response_model=ApproveAgentRunResponse)
async def approve_agent_run(run_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentRun).where(AgentRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AgentRun not found")

    run.approved_by = "Human Reviewer"
    run.approved_at = datetime.now(timezone.utc)
    run.status = "RUNNING"

    p_result = await db.execute(select(Project).where(Project.id == run.project_id))
    project = p_result.scalar_one_or_none()

    state = StateManager.create_initial_state(
        run_id=run.id,
        project_id=run.project_id,
        user_task=run.user_task,
        incident_id=run.incident_id
    )
    state.status = "RUNNING"
    state.current_step = run.current_step
    state.iteration_count = run.iteration_count
    state.run_context["approved"] = True
    state.run_context["default_branch"] = project.default_branch if project else "main"
    state.run_context["db_session"] = db

    runtime = AgentRuntime()
    final_state = await runtime.resume_after_approval(state, repository_snapshot=project.repository_snapshot if project else None)

    _sync_state_to_run(run, final_state)
    await db.commit()
    await db.refresh(run)

    is_mock = run.pull_request_status == "MOCK_CREATED" or run.pull_request_status != "CREATED"

    return ApproveAgentRunResponse(
        run_id=run.id,
        status=run.status,
        message="Agent run approved successfully. Mock Pull Request generated." if is_mock else "Agent run approved successfully. GitHub Pull Request created.",
        pull_request_url=run.pull_request_url,
        provider="mock" if is_mock else "github",
        is_mock=is_mock,
        pull_request_status=run.pull_request_status
    )


@router.post("/runs/{run_id}/cancel", response_model=AgentRunResponse)
async def cancel_agent_run(run_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentRun).where(AgentRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AgentRun not found")

    run.status = "CANCELLED"
    run.completed_at = datetime.now(timezone.utc)
    run.finished_at = run.completed_at
    await db.commit()
    await db.refresh(run)
    return _map_agent_run_response(run)
