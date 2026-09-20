from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class BrowserRunCreateRequest(BaseModel):
    project_id: str
    workspace_id: str
    scenario_id: str = "login-smoke"
    base_url: str = "http://localhost:3000"
    agent_run_id: Optional[str] = None
    use_mock: bool = True

class BrowserStepResultResponse(BaseModel):
    step_index: int
    action: str
    selector: Optional[str] = None
    selector_strategy: str = "STABLE_CSS"
    status: str = "PASSED"
    duration_ms: int = 0
    error: Optional[str] = None
    screenshot_path: Optional[str] = None
    observed_value: Optional[str] = None

class BrowserRunResponse(BaseModel):
    id: str
    project_id: str
    agent_run_id: Optional[str] = None
    workspace_id: str
    scenario_id: str
    provider_type: str
    status: str
    base_url: str
    current_url: Optional[str] = None
    duration_ms: int = 0
    step_count: int = 0
    passed_steps: int = 0
    failed_steps: int = 0
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    suspected_file: Optional[str] = None
    step_results: List[BrowserStepResultResponse] = []
    console_errors: Optional[List[Dict[str, Any]]] = None
    network_errors: Optional[List[Dict[str, Any]]] = None
    screenshot_paths: Optional[List[str]] = None
    created_at: Any
