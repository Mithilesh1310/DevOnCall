from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone

class BrowserAction(str, Enum):
    NAVIGATE = "NAVIGATE"
    CLICK = "CLICK"
    FILL = "FILL"
    SELECT = "SELECT"
    ASSERT_VISIBLE = "ASSERT_VISIBLE"
    ASSERT_TEXT = "ASSERT_TEXT"
    ASSERT_URL = "ASSERT_URL"
    WAIT_FOR = "WAIT_FOR"
    SCREENSHOT = "SCREENSHOT"

class SelectorStrategy(str, Enum):
    DATA_TESTID = "DATA_TESTID"
    ACCESSIBLE_ROLE = "ACCESSIBLE_ROLE"
    LABEL = "LABEL"
    STABLE_CSS = "STABLE_CSS"
    FRAGILE_CSS = "FRAGILE_CSS"

class BrowserStep(BaseModel):
    step_index: int = 0
    action: BrowserAction
    selector: Optional[str] = None
    value: Optional[str] = None
    expected_text: Optional[str] = None
    path: Optional[str] = None
    timeout_ms: int = 5000

class BrowserScenario(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    base_url: str = "http://localhost:3000"
    steps: List[BrowserStep] = []

class BrowserFailureType(str, Enum):
    ELEMENT_NOT_FOUND = "ELEMENT_NOT_FOUND"
    ASSERTION_FAILED = "ASSERTION_FAILED"
    NAVIGATION_FAILED = "NAVIGATION_FAILED"
    TIMEOUT = "TIMEOUT"
    CONSOLE_ERROR = "CONSOLE_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    APPLICATION_ERROR = "APPLICATION_ERROR"
    BROWSER_CRASH = "BROWSER_CRASH"
    BLOCKED_URL = "BLOCKED_URL"
    SCENARIO_INVALID = "SCENARIO_INVALID"
    APPLICATION_NOT_READY = "APPLICATION_NOT_READY"
    UNKNOWN = "UNKNOWN"

class BrowserRunStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    BLOCKED = "BLOCKED"
    ERROR = "ERROR"

class ConsoleLogEvent(BaseModel):
    level: str  # INFO, WARNING, ERROR
    text: str
    location: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class NetworkErrorEvent(BaseModel):
    url: str
    method: str
    status_code: int
    resource_type: Optional[str] = None
    failure_text: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class BrowserStepResult(BaseModel):
    step_index: int
    action: BrowserAction
    selector: Optional[str] = None
    selector_strategy: SelectorStrategy = SelectorStrategy.STABLE_CSS
    status: BrowserRunStatus = BrowserRunStatus.PASSED
    duration_ms: int = 0
    error: Optional[str] = None
    screenshot_path: Optional[str] = None
    observed_value: Optional[str] = None

class BrowserRunResult(BaseModel):
    id: str
    project_id: str
    agent_run_id: Optional[str] = None
    workspace_id: str
    scenario_id: str
    provider_type: str  # MOCK_BROWSER vs PLAYWRIGHT_BROWSER
    status: BrowserRunStatus
    base_url: str
    current_url: Optional[str] = None
    duration_ms: int = 0
    step_count: int = 0
    passed_steps: int = 0
    failed_steps: int = 0
    error_type: Optional[BrowserFailureType] = None
    error_message: Optional[str] = None
    suspected_file: Optional[str] = None
    step_results: List[BrowserStepResult] = []
    console_errors: List[ConsoleLogEvent] = []
    network_errors: List[NetworkErrorEvent] = []
    screenshot_paths: List[str] = []
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

