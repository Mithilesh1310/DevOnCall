from datetime import datetime, timezone
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class FailureType(str, Enum):
    TEST_FAILURE = "TEST_FAILURE"
    BUILD_FAILURE = "BUILD_FAILURE"
    TYPE_ERROR = "TYPE_ERROR"
    LINT_FAILURE = "LINT_FAILURE"
    DEPENDENCY_ERROR = "DEPENDENCY_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    TIMEOUT = "TIMEOUT"
    RESOURCE_LIMIT = "RESOURCE_LIMIT"
    UNKNOWN = "UNKNOWN"

class FailureDiagnostic(BaseModel):
    message: str
    file: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None
    code: Optional[str] = None
    source: str = "stderr"
    raw_snippet: Optional[str] = None

class ValidationResult(BaseModel):
    sandbox_run_id: str
    status: str  # PASSED, FAILED, TIMED_OUT, BLOCKED, ERROR
    command_type: str  # TEST, BUILD, LINT, TYPECHECK
    exit_code: int = 0
    summary: str
    stdout: str = ""
    stderr: str = ""
    failure_type: Optional[FailureType] = None
    diagnostics: List[FailureDiagnostic] = Field(default_factory=list)
    affected_files: List[str] = Field(default_factory=list)
    suggested_action: str = "CONTINUE"  # CONTINUE, FIX, RETRY, STOP, HUMAN_REVIEW

class RepairAttempt(BaseModel):
    iteration: int
    failure_type: str
    diagnostic: Optional[str] = None
    files_changed: List[str] = Field(default_factory=list)
    validation_before: Optional[str] = None
    validation_after: Optional[str] = None
    result: str = "PENDING"  # PASSED, FAILED

class AgentDecision(BaseModel):
    action: str  # FIX, RETRY, CONTINUE, STOP, HUMAN_REVIEW
    reason: str
    confidence: float = 1.0
    evidence: List[str] = Field(default_factory=list)
    target_files: List[str] = Field(default_factory=list)
