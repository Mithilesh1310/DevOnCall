from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class SandboxResult(BaseModel):
    status: str  # PASSED, FAILED, TIMED_OUT, BLOCKED, ERROR
    exit_code: int = -1
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    provider_type: str = "MOCK_SANDBOX"
    command_type: str = "TEST"
    runtime: str = "python"
    error_message: Optional[str] = None
