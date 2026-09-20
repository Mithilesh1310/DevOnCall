from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from app.services.sandbox.base import CommandType, SandboxStatus, SandboxProviderType

class SandboxRunCreateRequest(BaseModel):
    project_id: str = Field(..., description="Target project ID")
    workspace_id: str = Field(..., description="Target Phase 3 workspace ID")
    command_type: CommandType = Field(CommandType.TEST, description="Structured command type: TEST, BUILD, LINT, TYPECHECK")
    agent_run_id: Optional[str] = Field(None, description="Associated AgentRun ID if applicable")
    runtime: str = Field("python", description="Target runtime (python, node, typescript)")
    force_mock: bool = Field(False, description="Explicitly force MockSandboxProvider execution")

class SandboxRunResponse(BaseModel):
    id: str
    project_id: str
    agent_run_id: Optional[str] = None
    workspace_id: str
    command_type: str
    runtime: str
    provider_type: str
    status: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    timeout_seconds: int
    resource_limits: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
