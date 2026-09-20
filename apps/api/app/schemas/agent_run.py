from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict

class CreateAgentRunRequest(BaseModel):
    project_id: str
    task: str
    incident_id: Optional[str] = None

AgentRunCreate = CreateAgentRunRequest


class ToolCallRecordSchema(BaseModel):
    tool_name: str
    input_params: Dict[str, Any]
    success: bool
    summary: str
    started_at: datetime
    completed_at: datetime
    error: Optional[str] = None

class AgentRunResponse(BaseModel):
    id: str
    project_id: str
    incident_id: Optional[str] = None
    user_task: str
    status: str
    current_goal: Optional[str] = None
    current_step: int
    iteration_count: int
    summary: Optional[str] = None
    tool_calls: List[ToolCallRecordSchema] = []
    workspace_path: Optional[str] = None
    agent_branch: Optional[str] = None
    change_plan: Optional[Dict[str, Any]] = None
    diff_summary: Optional[Dict[str, Any]] = None
    pull_request_url: Optional[str] = None
    pull_request_status: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApproveAgentRunResponse(BaseModel):
    run_id: str
    status: str
    message: str
    pull_request_url: Optional[str] = None
    provider: Optional[str] = "mock"
    is_mock: Optional[bool] = True
    pull_request_status: Optional[str] = None
