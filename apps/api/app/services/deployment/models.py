from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class ReleaseCandidateStatus(str, Enum):
    CREATED = "CREATED"
    STAGING_PENDING = "STAGING_PENDING"
    STAGING_PASSED = "STAGING_PASSED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    CANARY_PENDING = "CANARY_PENDING"
    CANARY_DEPLOYED = "CANARY_DEPLOYED"
    CANARY_VERIFYING = "CANARY_VERIFYING"
    CANARY_VERIFIED = "CANARY_VERIFIED"
    CANARY_PASSED = "CANARY_PASSED"
    CANARY_FAILED = "CANARY_FAILED"
    FULL_DEPLOY_PENDING = "FULL_DEPLOY_PENDING"
    DEPLOYED = "DEPLOYED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    ROLLED_BACK = "ROLLED_BACK"


class ApprovalType(str, Enum):
    CANARY_RELEASE = "CANARY_RELEASE"
    FULL_PRODUCTION = "FULL_PRODUCTION"
    STAGING_TO_CANARY = "STAGING_TO_CANARY"
    CANARY_TO_FULL_PRODUCTION = "CANARY_TO_FULL_PRODUCTION"
    ROLLBACK = "ROLLBACK"


class ApprovalDecision(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class CanaryStatus(str, Enum):
    QUEUED = "QUEUED"
    DEPLOYING = "DEPLOYING"
    DEPLOYED = "DEPLOYED"
    PROMOTED = "PROMOTED"
    VERIFYING = "VERIFYING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class CanaryVerdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class RollbackStatus(str, Enum):
    ROLLBACK_REQUESTED = "ROLLBACK_REQUESTED"
    ROLLING_BACK = "ROLLING_BACK"
    ROLLED_BACK = "ROLLED_BACK"
    COMPLETED = "COMPLETED"
    ROLLBACK_FAILED = "ROLLBACK_FAILED"


class CanaryPolicyConfig(BaseModel):
    """
    Configurable per-project thresholds for Canary deployment verification.
    """
    min_observation_count: int = 20
    max_error_rate: float = 0.02
    max_latency_multiplier: float = 1.5
    max_new_critical_incidents: int = 0
    observation_window_seconds: int = 300


class ReleaseCandidateData(BaseModel):
    id: Optional[str] = None
    project_id: str = "demo-project"
    source_branch: str = "main"
    commit_sha: str
    pull_request_id: Optional[str] = None
    pr_url: Optional[str] = None
    staging_deployment_id: Optional[str] = None
    staging_verification_status: str = "PASSED"
    browser_verification_status: str = "PASSED"
    created_by: str = "DevOnCall Release Agent"
    status: ReleaseCandidateStatus = ReleaseCandidateStatus.CREATED
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ProductionApprovalData(BaseModel):
    id: Optional[str] = None
    rc_id: str
    approver_id: str
    approval_type: ApprovalType
    decision: ApprovalDecision = ApprovalDecision.APPROVED
    reason: Optional[str] = "Explicit human approval granted"
    confirmation_token: Optional[str] = None
    expires_at: Optional[Any] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    decided_at: Optional[Any] = None


class CanaryDeploymentData(BaseModel):
    id: Optional[str] = None
    rc_id: str
    traffic_percent: float = 5.0
    status: CanaryStatus = CanaryStatus.QUEUED
    deployment_url: Optional[str] = None
    error_message: Optional[str] = None
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: Optional[str] = None


class CanaryVerificationData(BaseModel):
    id: Optional[str] = None
    canary_id: str
    verdict: CanaryVerdict = CanaryVerdict.PASS
    metrics: Optional[Dict[str, Any]] = None
    insufficient_data_reasons: Optional[Dict[str, Any]] = None
    evaluated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ProductionDeploymentData(BaseModel):
    id: Optional[str] = None
    rc_id: str
    status: str = "SUCCESS"
    deployment_url: Optional[str] = None
    error_message: Optional[str] = None
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: Optional[str] = None


class RollbackRecordData(BaseModel):
    id: Optional[str] = None
    rc_id: str
    target_commit_sha: str
    status: RollbackStatus = RollbackStatus.COMPLETED
    reason: str
    initiated_by: str
    initiated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
