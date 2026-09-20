import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.session import get_db
from app.models.deployment import (
    ReleaseCandidateModel,
    ProductionApprovalModel,
    CanaryDeploymentModel,
    CanaryVerificationRecordModel,
    ProductionDeploymentModel,
    RollbackRecordModel,
    DeploymentAuditLogModel,
)
from app.schemas.deployment import (
    CreateReleaseCandidateRequest,
    ApprovalDecisionRequest,
    StartCanaryRequest,
    VerifyCanaryRequest,
    DeployProductionRequest,
    RollbackRequest,
    ReleaseCandidateResponse,
    ProductionApprovalResponse,
    CanaryDeploymentResponse,
    CanaryVerificationResponse,
    ProductionDeploymentResponse,
    RollbackRecordResponse,
)
from app.services.deployment.manager import DeploymentManager
from app.services.deployment.security import DeploymentSecurityPolicy
from app.services.deployment.models import ApprovalType, ApprovalDecision

logger = logging.getLogger("devoncall.endpoints.deployment")
router = APIRouter()


@router.post("/release-candidates", response_model=ReleaseCandidateResponse)
async def create_release_candidate(
    req: CreateReleaseCandidateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Creates a new Release Candidate.
    Requires exact 40-character commit SHA and valid staging deployment state.
    """
    valid_sha, sha_msg = DeploymentSecurityPolicy.validate_commit_sha(req.commit_sha)
    if not valid_sha:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"INVALID_COMMIT_SHA: {sha_msg}",
        )

    manager = DeploymentManager()
    rc = manager.create_release_candidate(
        project_id=req.project_id,
        commit_sha=req.commit_sha,
        staging_deployment_id=req.staging_deployment_id,
        pr_url=req.pr_url,
    )

    db_rc = ReleaseCandidateModel(
        id=rc.id,
        project_id=rc.project_id,
        commit_sha=rc.commit_sha,
        staging_deployment_id=rc.staging_deployment_id,
        pr_url=rc.pr_url,
        status=rc.status.value,
    )
    db.add(db_rc)
    await db.commit()
    await db.refresh(db_rc)

    return ReleaseCandidateResponse(
        id=db_rc.id,
        project_id=db_rc.project_id,
        commit_sha=db_rc.commit_sha,
        staging_deployment_id=db_rc.staging_deployment_id,
        pr_url=db_rc.pr_url,
        status=db_rc.status,
        approvals=[],
        canary_deployments=[],
        production_deployments=[],
        created_at=db_rc.created_at,
        updated_at=db_rc.updated_at,
    )


@router.get("/release-candidates", response_model=List[ReleaseCandidateResponse])
async def list_release_candidates(db: AsyncSession = Depends(get_db)):
    """List all release candidates."""
    res = await db.execute(select(ReleaseCandidateModel).order_by(ReleaseCandidateModel.created_at.desc()))
    rcs = res.scalars().all()

    out = []
    for rc in rcs:
        out.append(
            ReleaseCandidateResponse(
                id=rc.id,
                project_id=rc.project_id,
                commit_sha=rc.commit_sha,
                staging_deployment_id=rc.staging_deployment_id,
                pr_url=rc.pr_url,
                status=rc.status,
                created_at=rc.created_at,
                updated_at=rc.updated_at,
            )
        )
    return out


@router.get("/release-candidates/{rc_id}", response_model=ReleaseCandidateResponse)
async def get_release_candidate(rc_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve release candidate by ID."""
    res = await db.execute(select(ReleaseCandidateModel).where(ReleaseCandidateModel.id == rc_id))
    rc = res.scalar_one_or_none()
    if not rc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Release Candidate '{rc_id}' not found.")

    return ReleaseCandidateResponse(
        id=rc.id,
        project_id=rc.project_id,
        commit_sha=rc.commit_sha,
        staging_deployment_id=rc.staging_deployment_id,
        pr_url=rc.pr_url,
        status=rc.status,
        created_at=rc.created_at,
        updated_at=rc.updated_at,
    )


@router.post("/release-candidates/{rc_id}/approve", response_model=ProductionApprovalResponse)
async def submit_approval(
    rc_id: str,
    req: ApprovalDecisionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Submits a human approval decision for Canary Release or Full Production Deployment.
    Requires authenticated approver and valid confirmation token.
    """
    manager = DeploymentManager()
    try:
        appr_type = ApprovalType(req.approval_type)
        decision = ApprovalDecision(req.decision)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    appr_data, err = manager.request_approval(
        rc_id=rc_id,
        approval_type=appr_type,
        approver_id=req.approver_id,
        decision=decision,
        reason=req.reason,
        token=req.confirmation_token,
    )
    if err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)

    return ProductionApprovalResponse(
        id=appr_data.id,
        rc_id=appr_data.rc_id,
        approval_type=appr_data.approval_type.value,
        approver_id=appr_data.approver_id,
        decision=appr_data.decision.value,
        reason=appr_data.reason,
        confirmation_token=appr_data.confirmation_token,
        expires_at=appr_data.expires_at,
        created_at=appr_data.created_at,
        decided_at=appr_data.decided_at,
    )


@router.post("/release-candidates/{rc_id}/canary", response_model=CanaryDeploymentResponse)
async def start_canary(
    rc_id: str,
    req: StartCanaryRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Triggers Canary Deployment for an approved Release Candidate.
    Traffic percentage strictly bounded between 1.0% and 10.0%.
    """
    manager = DeploymentManager()
    canary, err = manager.start_canary(
        rc_id=rc_id,
        traffic_percent=req.traffic_percent,
        token=req.confirmation_token,
        mock_scenario=req.mock_scenario,
    )
    if err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)

    return CanaryDeploymentResponse(
        id=canary.id,
        rc_id=canary.rc_id,
        traffic_percent=canary.traffic_percent,
        status=canary.status.value,
        deployment_url=canary.deployment_url,
        error_message=canary.error_message,
        started_at=canary.started_at,
        finished_at=canary.finished_at,
    )


@router.post("/canary/{canary_id}/verify", response_model=CanaryVerificationResponse)
async def verify_canary(
    canary_id: str,
    req: VerifyCanaryRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Evaluates canary telemetry against baseline metrics using the Canary Decision Engine.
    Returns verdict PASS, FAIL, INSUFFICIENT_DATA, or HUMAN_REVIEW.
    """
    manager = DeploymentManager()
    verif = manager.verify_canary(canary_id=canary_id, scenario=req.mock_scenario)

    return CanaryVerificationResponse(
        id=verif.id,
        canary_id=verif.canary_id,
        verdict=verif.verdict.value,
        metrics=verif.metrics,
        insufficient_data_reasons=verif.insufficient_data_reasons,
        evaluated_at=verif.evaluated_at,
    )


@router.post("/release-candidates/{rc_id}/deploy", response_model=ProductionDeploymentResponse)
async def deploy_production(
    rc_id: str,
    req: DeployProductionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Executes Full Production Deployment.
    Requires prior Canary Verification PASS and explicit double human approval.
    """
    manager = DeploymentManager()
    dep, err = manager.deploy_production(
        rc_id=rc_id,
        token=req.confirmation_token,
        mock_scenario=req.mock_scenario,
    )
    if err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)

    return ProductionDeploymentResponse(
        id=dep.id,
        rc_id=dep.rc_id,
        status=dep.status,
        deployment_url=dep.deployment_url,
        error_message=dep.error_message,
        started_at=dep.started_at,
        finished_at=dep.finished_at,
    )


@router.post("/release-candidates/{rc_id}/rollback", response_model=RollbackRecordResponse)
async def rollback_production(
    rc_id: str,
    req: RollbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Initiates emergency or automated rollback to target stable commit SHA.
    Requires exact 40-character target commit SHA.
    """
    manager = DeploymentManager()
    roll, err = manager.rollback(
        rc_id=rc_id,
        target_commit_sha=req.target_commit_sha,
        reason=req.reason,
        initiated_by=req.initiated_by,
        token=req.confirmation_token,
        mock_scenario=req.mock_scenario,
    )
    if err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)

    return RollbackRecordResponse(
        id=roll.id,
        rc_id=roll.rc_id,
        target_commit_sha=roll.target_commit_sha,
        status=roll.status.value,
        reason=roll.reason,
        initiated_by=roll.initiated_by,
        initiated_at=roll.initiated_at,
        completed_at=roll.completed_at,
    )


@router.get("/release-candidates/{rc_id}/audit")
async def get_deployment_audit_log(rc_id: str):
    """Retrieves execution audit log events for a release candidate."""
    manager = DeploymentManager()
    logs = manager.get_audit_logs(rc_id)
    return {"rc_id": rc_id, "audit_logs": logs}
