from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel, ConfigDict
from app.services.agent.policies import ToolPermission, AgentPolicy, default_phase3_policy
from app.services.agent.models import ToolResult, ToolError

class ToolContext(BaseModel):
    """
    Controlled context provided to tools during execution.
    Exposes only essential metadata, snapshot, and permission policies.
    """
    run_id: str
    project_id: str
    repository_snapshot: Optional[Dict[str, Any]] = None
    policy: AgentPolicy = default_phase3_policy
    run_context: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class BaseTool(ABC):
    """
    Abstract interface for all DevOnCall tools.
    Requires explicit permission levels, input/output schemas, and structured results.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @property
    @abstractmethod
    def permission_level(self) -> ToolPermission:
        pass

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {}

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {}

    @abstractmethod
    async def execute(self, input_params: Dict[str, Any], context: ToolContext) -> ToolResult:
        pass
