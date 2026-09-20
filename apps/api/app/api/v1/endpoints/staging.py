import logging
from typing import List, Optional
from fastapi import APIRouter, Request, Header, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.session import get_db
from app.models.staging import StagingDeploymentModel, StagingCheckResultModel
from app.schemas.staging import (
    StagingDeploymentCreateRequest,
    StagingDeploymentResponse,
    StagingCheckResultResponse,
)
from app.services.staging.manager import StagingManager
from app.services.staging.policies import StagingSecurityPolicy, StagingVerificationPolicy
from app.services.staging.models import StagingDeploymentStatus

logger = logging.getLogger("devoncall.endpoints.staging")
router = APIRouter()


@router.post("/deployments", response_model=StagingDeploymentResponse)
async def create_staging_deployment(
    req: StagingDeploymentCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Triggers an isolated Staging Deployment & Autonomous Verification Gate.
    Strictly REJECTS any environment specification other than 'STAGING'.
    """
    # 1. Mandatory Production Environment Rejection Security Policy
    is_valid_env, env_reason = StagingSecurityPolicy.validate_environment(req.environment)
    if not is_valid_env:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"SECURITY_POLICY_VIOLATION: {env_reason}",
        )

    # 2. Mandatory Commit & Branch Validation
    is_valid_commit, commit_reason = StagingSecurityPolicy.validate_commit(req.commit_sha, req.branch)
    if not is_valid_commit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"COMMIT_VALIDATION_FAILED: {commit_reason}",
        )

    # 3. Instantiate StagingManager
    policy = StagingVerificationPolicy(
        require_build=True,
        require_health=True,
        require_smoke=True,
        require_browser=req.require_browser,
    )
    manager = StagingManager(use_mock=req.use_mock)

    run_res = await manager.create_and_run_deployment(
        project_id=req.project_id,
        workspace_id=req.workspace_id,
        branch=req.branch,
        commit_sha=req.commit_sha,
        agent_run_id=req.agent_run_id,
        environment="STAGING",
        use_mock=req.use_mock,
        mock_scenario=req.mock_scenario,
        verification_policy=policy,
    )

    # 4. Persist StagingDeploymentModel to DB
    db_deployment = StagingDeploymentModel(
        id=run_res.id,
        project_id=run_res.project_id,
        agent_run_id=run_res.agent_run_id,
        workspace_id=run_res.workspace_id,
        branch=run_res.branch,
        commit_sha=run_res.commit_sha,
        environment=run_res.environment,
        provider=run_res.provider,
        status=run_res.status.value,
        deployment_url=run_res.deployment_url,
        health_status=run_res.health_status,
        duration_ms=run_res.duration_ms,
        error_type=run_res.error_type,
        error_message=run_res.error_message,
    )
    db.add(db_deployment)

    for chk in run_res.checks:
        db_chk = StagingCheckResultModel(
            id=chk.id,
            deployment_id=run_res.id,
            check_type=chk.check_type.value,
            status=chk.status.value,
            duration_ms=chk.duration_ms,
            summary=chk.summary,
            details=chk.details,
        )
        db.add(db_chk)

    await db.commit()
    await db.refresh(db_deployment)

    # Convert checks for response
    checks_out = [
        StagingCheckResultResponse(
            id=c.id,
            check_type=c.check_type,
            status=c.status,
            duration_ms=c.duration_ms,
            summary=c.summary,
            details=c.details,
            created_at=c.created_at,
        )
        for c in run_res.checks
    ]

    return StagingDeploymentResponse(
        id=db_deployment.id,
        project_id=db_deployment.project_id,
        agent_run_id=db_deployment.agent_run_id,
        workspace_id=db_deployment.workspace_id,
        branch=db_deployment.branch,
        commit_sha=db_deployment.commit_sha,
        environment=db_deployment.environment,
        provider=db_deployment.provider,
        status=db_deployment.status,
        deployment_url=db_deployment.deployment_url,
        health_status=db_deployment.health_status,
        duration_ms=db_deployment.duration_ms,
        error_type=db_deployment.error_type,
        error_message=db_deployment.error_message,
        checks=checks_out,
        started_at=db_deployment.started_at,
        finished_at=db_deployment.finished_at,
        created_at=db_deployment.created_at,
    )


@router.get("/deployments", response_model=List[StagingDeploymentResponse])
async def list_staging_deployments(db: AsyncSession = Depends(get_db)):
    """List all staging deployments."""
    res = await db.execute(select(StagingDeploymentModel).order_by(StagingDeploymentModel.created_at.desc()))
    deployments = res.scalars().all()

    out = []
    for d in deployments:
        chks_res = await db.execute(
            select(StagingCheckResultModel).where(StagingCheckResultModel.deployment_id == d.id)
        )
        chks = chks_res.scalars().all()
        checks_out = [
            StagingCheckResultResponse(
                id=c.id,
                check_type=c.check_type,
                status=c.status,
                duration_ms=c.duration_ms,
                summary=c.summary,
                details=c.details,
                created_at=c.created_at,
            )
            for c in chks
        ]
        out.append(
            StagingDeploymentResponse(
                id=d.id,
                project_id=d.project_id,
                agent_run_id=d.agent_run_id,
                workspace_id=d.workspace_id,
                branch=d.branch,
                commit_sha=d.commit_sha,
                environment=d.environment,
                provider=d.provider,
                status=d.status,
                deployment_url=d.deployment_url,
                health_status=d.health_status,
                duration_ms=d.duration_ms,
                error_type=d.error_type,
                error_message=d.error_message,
                checks=checks_out,
                started_at=d.started_at,
                finished_at=d.finished_at,
                created_at=d.created_at,
            )
        )
    return out


@router.get("/deployments/{id}", response_model=StagingDeploymentResponse)
async def get_staging_deployment(id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve staging deployment by ID."""
    res = await db.execute(select(StagingDeploymentModel).where(StagingDeploymentModel.id == id))
    d = res.scalar_one_or_none()
    if not d:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Staging deployment '{id}' not found.")

    chks_res = await db.execute(select(StagingCheckResultModel).where(StagingCheckResultModel.deployment_id == d.id))
    chks = chks_res.scalars().all()
    checks_out = [
        StagingCheckResultResponse(
            id=c.id,
            check_type=c.check_type,
            status=c.status,
            duration_ms=c.duration_ms,
            summary=c.summary,
            details=c.details,
            created_at=c.created_at,
        )
        for c in chks
    ]
    return StagingDeploymentResponse(
        id=d.id,
        project_id=d.project_id,
        agent_run_id=d.agent_run_id,
        workspace_id=d.workspace_id,
        branch=d.branch,
        commit_sha=d.commit_sha,
        environment=d.environment,
        provider=d.provider,
        status=d.status,
        deployment_url=d.deployment_url,
        health_status=d.health_status,
        duration_ms=d.duration_ms,
        error_type=d.error_type,
        error_message=d.error_message,
        checks=checks_out,
        started_at=d.started_at,
        finished_at=d.finished_at,
        created_at=d.created_at,
    )


@router.get("/deployments/{id}/checks", response_model=List[StagingCheckResultResponse])
async def get_staging_checks(id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve checks for a staging deployment."""
    chks_res = await db.execute(select(StagingCheckResultModel).where(StagingCheckResultModel.deployment_id == id))
    chks = chks_res.scalars().all()
    return [
        StagingCheckResultResponse(
            id=c.id,
            check_type=c.check_type,
            status=c.status,
            duration_ms=c.duration_ms,
            summary=c.summary,
            details=c.details,
            created_at=c.created_at,
        )
        for c in chks
    ]


@router.post("/deployments/{id}/cancel")
async def cancel_staging_deployment(id: str, db: AsyncSession = Depends(get_db)):
    """Cancel a staging deployment and tear down resources."""
    res = await db.execute(select(StagingDeploymentModel).where(StagingDeploymentModel.id == id))
    d = res.scalar_one_or_none()
    if not d:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Staging deployment '{id}' not found.")

    d.status = "CANCELLED"
    await db.commit()

    manager = StagingManager(use_mock=True)
    await manager.cleanup_manager.cleanup_deployment(id)

    return {"status": "CANCELLED", "deployment_id": id}


@router.post("/deployments/{id}/cleanup")
async def cleanup_staging_deployment(id: str, db: AsyncSession = Depends(get_db)):
    """Manually cleanup staging resources for deployment."""
    manager = StagingManager(use_mock=True)
    success = await manager.cleanup_manager.cleanup_deployment(id)
    return {"status": "CLEANED_UP" if success else "FAILED", "deployment_id": id}
