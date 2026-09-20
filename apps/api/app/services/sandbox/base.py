from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel
from app.services.sandbox.result import SandboxResult

class CommandType(str, Enum):
    TEST = "TEST"
    BUILD = "BUILD"
    LINT = "LINT"
    TYPECHECK = "TYPECHECK"

class SandboxStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"
    BLOCKED = "BLOCKED"
    ERROR = "ERROR"

class SandboxProviderType(str, Enum):
    MOCK_SANDBOX = "MOCK_SANDBOX"
    DOCKER_SANDBOX = "DOCKER_SANDBOX"

class BaseSandboxProvider(ABC):
    """
    Abstract base class for all DevOnCall sandbox providers.
    """

    @property
    @abstractmethod
    def provider_type(self) -> SandboxProviderType:
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Checks whether the sandbox environment/daemon is available."""
        pass

    @abstractmethod
    async def run_validation(
        self,
        workspace_path: str,
        command_type: CommandType,
        command_str: str,
        runtime: str = "python",
        timeout_seconds: int = 120,
        cpu_limit: float = 2.0,
        memory_limit: str = "1g",
        max_output_bytes: int = 2097152
    ) -> SandboxResult:
        """Executes validation inside isolated sandbox."""
        pass
