from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class SentryStackFrame(BaseModel):
    file: str
    line: Optional[int] = None
    column: Optional[int] = None
    function: Optional[str] = None
    module: Optional[str] = None
    in_app: bool = True
    raw_frame: Optional[str] = None

class SentryIncident(BaseModel):
    event_id: str
    issue_id: str
    project_slug: str
    environment: str = "production"
    release: Optional[str] = None
    commit_sha: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error_type: str
    error_message: str
    culprit: Optional[str] = None
    stack_trace: List[SentryStackFrame] = Field(default_factory=list)
    occurrence_count: int = 1
    url: Optional[str] = None
    tags: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source: str = "SENTRY"
    is_mock: bool = False

class SentryRawPayload(BaseModel):
    action: Optional[str] = "created"
    data: Dict[str, Any] = Field(default_factory=dict)
    installation: Optional[Dict[str, Any]] = None
