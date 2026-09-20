from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class CreateReleaseCandidateRequest(BaseModel):
    project_id: str
    commit_sha: str = Field(..., description="Exact 40-character git commit SHA.")
    staging_deployment_id: Optional[str] = None
    pr_url: Optional[str] = None


class ApprovalDecisionRequest(BaseModel):
    rc_id: str
    approval_type: str = Field(..., description="CANARY_RELEASE or FULL_PRODUCTION.")
    approver_id: str
    decision: str = Field(..., description="APPROVED or REJECTED.")
    reason: Optional[str] = None
    confirmation_token: Optional[str] = None


class StartCanaryRequest(BaseModel):
    rc_id: str
    traffic_percent: float = Field(5.0, ge=1.0, le=10.0, description="Traffic percentage for canary release (1-10%).")
    confirmation_token: Optional[str] = None
    mock_scenario: str = "HEALTHY"


class VerifyCanaryRequest(BaseModel):
    canary_id: str
    mock_scenario: str = "HEALTHY"  # HEALTHY, HIGH_ERROR_RATE, HIGH_LATENCY, INSUFFICIENT_DATA


class DeployProductionRequest(BaseModel):
    rc_id: str
    confirmation_token: Optional[str] = None
    mock_scenario: str = "SUCCESS"  # SUCCESS, DEPLOY_FAIL


class RollbackRequest(BaseModel):
    rc_id: str
    target_commit_sha: str = Field(..., description="Exact 40-character target git commit SHA.")
    reason: str
    initiated_by: str
    confirmation_token: Optional[str] = None
    mock_scenario: str = "SUCCESS"


class ProductionApprovalResponse(BaseModel):
    id: str
    rc_id: str
    approval_type: str
    approver_id: str
    decision: str
    reason: Optional[str] = None
    confirmation_token: Optional[str] = None
    expires_at: Optional[Any] = None
    created_at: Any
    decided_at: Optional[Any] = None


class CanaryVerificationResponse(BaseModel):
    id: str
    canary_id: str
    verdict: str
    metrics: Optional[Dict[str, Any]] = None
    insufficient_data_reasons: Optional[Dict[str, Any]] = None
    evaluated_at: Any


class CanaryDeploymentResponse(BaseModel):
    id: str
    rc_id: str
    traffic_percent: float
    status: str
    deployment_url: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Any
    finished_at: Optional[Any] = None
    verifications: List[CanaryVerificationResponse] = []


class ProductionDeploymentResponse(BaseModel):
    id: str
    rc_id: str
    status: str
    deployment_url: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Any
    finished_at: Optional[Any] = None


class RollbackRecordResponse(BaseModel):
    id: str
    rc_id: str
    target_commit_sha: str
    status: str
    reason: str
    initiated_by: str
    initiated_at: Any
    completed_at: Optional[Any] = None


class ReleaseCandidateResponse(BaseModel):
    id: str
    project_id: str
    commit_sha: str
    staging_deployment_id: Optional[str] = None
    pr_url: Optional[str] = None
    status: str
    approvals: List[ProductionApprovalResponse] = []
    canary_deployments: List[CanaryDeploymentResponse] = []
    production_deployments: List[ProductionDeploymentResponse] = []
    created_at: Any
    updated_at: Any
