import uuid
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class StagingDeploymentStatus(str, Enum):
    QUEUED = "QUEUED"
    BUILDING = "BUILDING"
    DEPLOYING = "DEPLOYING"
    HEALTH_CHECKING = "HEALTH_CHECKING"
    VERIFYING = "VERIFYING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"
    CANCELLED = "CANCELLED"
    BLOCKED = "BLOCKED"


class StagingCheckType(str, Enum):
    BUILD = "BUILD"
    DEPLOYMENT = "DEPLOYMENT"
    HEALTH = "HEALTH"
    SMOKE = "SMOKE"
    BROWSER = "BROWSER"
    SANDBOX = "SANDBOX"


class StagingCheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"
    BLOCKED = "BLOCKED"


class StagingCheckResult(BaseModel):
    id: str = Field(default_factory=lambda: f"sck-{uuid.uuid4().hex[:8]}")
    deployment_id: str
    check_type: StagingCheckType
    status: StagingCheckStatus = StagingCheckStatus.PASS
    duration_ms: int = 0
    summary: str
    details: Optional[Dict[str, Any]] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class StagingDeployment(BaseModel):
    id: str = Field(default_factory=lambda: f"stg-{uuid.uuid4().hex[:8]}")
    project_id: str
    agent_run_id: Optional[str] = None
    workspace_id: str
    branch: str
    commit_sha: str
    environment: str = "STAGING"
    provider: str = "MOCK_STAGING"  # MOCK_STAGING, DOCKER_STAGING
    status: StagingDeploymentStatus = StagingDeploymentStatus.QUEUED
    deployment_url: Optional[str] = None
    health_status: Optional[str] = None
    duration_ms: int = 0
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    checks: List[StagingCheckResult] = []
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
