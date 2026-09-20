from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseAgentOrchestrator(ABC):
    """
    Abstract interface boundary for DevOnCall AI agent engine.
    Ensures API endpoints never execute raw prompt logic directly.
    """

    @abstractmethod
    async def run_investigation(self, incident_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an investigation pipeline for a given incident.
        Must be implemented by concrete Agent execution engines in future phases.
        """
        pass
