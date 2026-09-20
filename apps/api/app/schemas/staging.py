from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class StagingDeploymentCreateRequest(BaseModel):
    project_id: str
    workspace_id: str
    branch: str
    commit_sha: str
    environment: str = Field("STAGING", description="Target deployment environment. Must be 'STAGING'.")
    agent_run_id: Optional[str] = None
    use_mock: bool = True
    mock_scenario: str = "PASS"  # PASS, BUILD_FAIL, DEPLOY_FAIL, HEALTH_FAIL, SMOKE_FAIL, BROWSER_FAIL
    require_browser: bool = False


class StagingCheckResultResponse(BaseModel):
    id: str
    check_type: str
    status: str
    duration_ms: int = 0
    summary: str
    details: Optional[Dict[str, Any]] = None
    created_at: Any


class StagingDeploymentResponse(BaseModel):
    id: str
    project_id: str
    agent_run_id: Optional[str] = None
    workspace_id: str
    branch: str
    commit_sha: str
    environment: str = "STAGING"
    provider: str
    status: str
    deployment_url: Optional[str] = None
    health_status: Optional[str] = None
    duration_ms: int = 0
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    checks: List[StagingCheckResultResponse] = []
    started_at: Any
    finished_at: Optional[Any] = None
    created_at: Any
