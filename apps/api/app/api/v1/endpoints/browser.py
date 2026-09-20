import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.session import get_db
from app.models.project import Project
from app.models.browser_run import BrowserRun, BrowserStepResultModel
from app.schemas.browser import BrowserRunCreateRequest, BrowserRunResponse, BrowserStepResultResponse
from app.services.browser import (
    BrowserManager,
    get_scenario,
    PREDEFINED_SCENARIOS,
    BrowserScenario,
    BrowserSecurityPolicy,
    MockBrowserProvider,
    PlaywrightBrowserProvider
)

logger = logging.getLogger("devoncall.api.browser")
router = APIRouter()

@router.post("/runs", response_model=BrowserRunResponse, status_code=status.HTTP_201_CREATED)
async def create_browser_run(
    req: BrowserRunCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Triggers a controlled browser UI verification run.
    Validates URL allowlist, security bounds, and scenario steps.
    """
    # 1. Validate Base URL Security
    policy = BrowserSecurityPolicy()
    is_valid, reason = policy.validate_url(req.base_url)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Security Policy Rejection: {reason}"
        )

    # 2. Retrieve Scenario
    scenario = get_scenario(req.scenario_id)
    if not scenario:
        scenario = PREDEFINED_SCENARIOS.get("login-smoke")

    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario '{req.scenario_id}' not found."
        )

    # Override base URL
    scenario = BrowserScenario(
        id=scenario.id,
        name=scenario.name,
        description=scenario.description,
        base_url=req.base_url,
        steps=scenario.steps
    )

    # 3. Execute Browser Run
    provider = MockBrowserProvider() if req.use_mock else PlaywrightBrowserProvider()
    manager = BrowserManager(provider=provider)

    try:
        run_res = await manager.execute_browser_validation(
            scenario=scenario,
            project_id=req.project_id,
            workspace_id=req.workspace_id,
            agent_run_id=req.agent_run_id
        )

        # 4. Persist to DB
        db_run = BrowserRun(
            id=run_res.id,
            project_id=run_res.project_id,
            agent_run_id=run_res.agent_run_id,
            workspace_id=run_res.workspace_id,
            scenario_id=run_res.scenario_id,
            provider_type=run_res.provider_type,
            status=run_res.status.value,
            base_url=run_res.base_url,
            current_url=run_res.current_url,
            duration_ms=run_res.duration_ms,
            step_count=run_res.step_count,
            passed_steps=run_res.passed_steps,
            failed_steps=run_res.failed_steps,
            error_type=run_res.error_type.value if run_res.error_type else None,
            error_message=run_res.error_message,
            suspected_file=run_res.suspected_file,
            artifact_paths={"screenshots": run_res.screenshot_paths},
            console_errors=[e.model_dump() for e in run_res.console_errors],
            network_errors=[e.model_dump() for e in run_res.network_errors]
        )
        db.add(db_run)

        for step in run_res.step_results:
            db_step = BrowserStepResultModel(
                browser_run_id=run_res.id,
                step_index=step.step_index,
                action=step.action.value,
                selector=step.selector,
                selector_strategy=step.selector_strategy.value,
                status=step.status.value,
                duration_ms=step.duration_ms,
                error=step.error,
                screenshot_path=step.screenshot_path,
                observed_value=step.observed_value
            )
            db.add(db_step)

        await db.commit()
        await db.refresh(db_run)

        # Build response
        step_responses = [
            BrowserStepResultResponse(
                step_index=s.step_index,
                action=s.action.value,
                selector=s.selector,
                selector_strategy=s.selector_strategy.value,
                status=s.status.value,
                duration_ms=s.duration_ms,
                error=s.error,
                screenshot_path=s.screenshot_path,
                observed_value=s.observed_value
            )
            for s in run_res.step_results
        ]

        return BrowserRunResponse(
            id=run_res.id,
            project_id=run_res.project_id,
            agent_run_id=run_res.agent_run_id,
            workspace_id=run_res.workspace_id,
            scenario_id=run_res.scenario_id,
            provider_type=run_res.provider_type,
            status=run_res.status.value,
            base_url=run_res.base_url,
            current_url=run_res.current_url,
            duration_ms=run_res.duration_ms,
            step_count=run_res.step_count,
            passed_steps=run_res.passed_steps,
            failed_steps=run_res.failed_steps,
            error_type=run_res.error_type.value if run_res.error_type else None,
            error_message=run_res.error_message,
            suspected_file=run_res.suspected_file,
            step_results=step_responses,
            console_errors=[e.model_dump() for e in run_res.console_errors],
            network_errors=[e.model_dump() for e in run_res.network_errors],
            screenshot_paths=run_res.screenshot_paths,
            created_at=run_res.created_at
        )

    except Exception as ex:
        logger.error(f"Browser run creation failed: {ex}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Browser verification execution failed: {ex}"
        )


@router.get("/runs", response_model=List[BrowserRunResponse])
async def list_browser_runs(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    workspace_id: Optional[str] = Query(None, description="Filter by workspace ID"),
    agent_run_id: Optional[str] = Query(None, description="Filter by agent run ID"),
    db: AsyncSession = Depends(get_db)
):
    query = select(BrowserRun).order_by(BrowserRun.created_at.desc())
    if project_id:
        query = query.where(BrowserRun.project_id == project_id)
    if workspace_id:
        query = query.where(BrowserRun.workspace_id == workspace_id)
    if agent_run_id:
        query = query.where(BrowserRun.agent_run_id == agent_run_id)

    res = await db.execute(query)
    runs = res.scalars().all()
    results = []
    for r in runs:
        steps_res = await db.execute(select(BrowserStepResultModel).where(BrowserStepResultModel.browser_run_id == r.id).order_by(BrowserStepResultModel.step_index))
        steps = steps_res.scalars().all()
        step_dtos = [
            BrowserStepResultResponse(
                step_index=s.step_index,
                action=s.action,
                selector=s.selector,
                selector_strategy=s.selector_strategy,
                status=s.status,
                duration_ms=s.duration_ms,
                error=s.error,
                screenshot_path=s.screenshot_path,
                observed_value=s.observed_value
            )
            for s in steps
        ]
        results.append(
            BrowserRunResponse(
                id=r.id,
                project_id=r.project_id,
                agent_run_id=r.agent_run_id,
                workspace_id=r.workspace_id,
                scenario_id=r.scenario_id,
                provider_type=r.provider_type,
                status=r.status,
                base_url=r.base_url,
                current_url=r.current_url,
                duration_ms=r.duration_ms,
                step_count=r.step_count,
                passed_steps=r.passed_steps,
                failed_steps=r.failed_steps,
                error_type=r.error_type,
                error_message=r.error_message,
                suspected_file=r.suspected_file,
                step_results=step_dtos,
                console_errors=r.console_errors,
                network_errors=r.network_errors,
                screenshot_paths=r.artifact_paths.get("screenshots") if r.artifact_paths else [],
                created_at=r.created_at
            )
        )
    return results


@router.get("/runs/{run_id}", response_model=BrowserRunResponse)
async def get_browser_run(
    run_id: str,
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(BrowserRun).where(BrowserRun.id == run_id))
    r = res.scalar_one_or_none()
    if not r:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"BrowserRun '{run_id}' not found."
        )

    steps_res = await db.execute(select(BrowserStepResultModel).where(BrowserStepResultModel.browser_run_id == r.id).order_by(BrowserStepResultModel.step_index))
    steps = steps_res.scalars().all()
    step_dtos = [
        BrowserStepResultResponse(
            step_index=s.step_index,
            action=s.action,
            selector=s.selector,
            selector_strategy=s.selector_strategy,
            status=s.status,
            duration_ms=s.duration_ms,
            error=s.error,
            screenshot_path=s.screenshot_path,
            observed_value=s.observed_value
        )
        for s in steps
    ]

    return BrowserRunResponse(
        id=r.id,
        project_id=r.project_id,
        agent_run_id=r.agent_run_id,
        workspace_id=r.workspace_id,
        scenario_id=r.scenario_id,
        provider_type=r.provider_type,
        status=r.status,
        base_url=r.base_url,
        current_url=r.current_url,
        duration_ms=r.duration_ms,
        step_count=r.step_count,
        passed_steps=r.passed_steps,
        failed_steps=r.failed_steps,
        error_type=r.error_type,
        error_message=r.error_message,
        suspected_file=r.suspected_file,
        step_results=step_dtos,
        console_errors=r.console_errors,
        network_errors=r.network_errors,
        screenshot_paths=r.artifact_paths.get("screenshots") if r.artifact_paths else [],
        created_at=r.created_at
    )


@router.get("/runs/{run_id}/steps", response_model=List[BrowserStepResultResponse])
async def get_browser_run_steps(
    run_id: str,
    db: AsyncSession = Depends(get_db)
):
    steps_res = await db.execute(select(BrowserStepResultModel).where(BrowserStepResultModel.browser_run_id == run_id).order_by(BrowserStepResultModel.step_index))
    steps = steps_res.scalars().all()
    return [
        BrowserStepResultResponse(
            step_index=s.step_index,
            action=s.action,
            selector=s.selector,
            selector_strategy=s.selector_strategy,
            status=s.status,
            duration_ms=s.duration_ms,
            error=s.error,
            screenshot_path=s.screenshot_path,
            observed_value=s.observed_value
        )
        for s in steps
    ]


@router.post("/runs/{run_id}/cancel", response_model=BrowserRunResponse)
async def cancel_browser_run(
    run_id: str,
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(BrowserRun).where(BrowserRun.id == run_id))
    r = res.scalar_one_or_none()
    if not r:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"BrowserRun '{run_id}' not found."
        )

    if r.status in ["RUNNING", "QUEUED"]:
        r.status = "CANCELLED"
        r.error_message = "Cancelled by user request"
        await db.commit()
        await db.refresh(r)

    return await get_browser_run(run_id, db)
