import asyncio
import logging
from datetime import datetime, timezone
from app.services.sandbox.base import BaseSandboxProvider, CommandType, SandboxProviderType, SandboxStatus
from app.services.sandbox.result import SandboxResult

logger = logging.getLogger("devoncall.sandbox.mock_provider")

class MockSandboxProvider(BaseSandboxProvider):
    """
    Deterministic Mock Sandbox Provider for unit tests and offline environments.
    """

    @property
    def provider_type(self) -> SandboxProviderType:
        return SandboxProviderType.MOCK_SANDBOX

    async def is_available(self) -> bool:
        return True

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
        started_at = datetime.now(timezone.utc)
        logger.info(f"[MOCK_SANDBOX] Running '{command_type}' ({command_str}) in workspace '{workspace_path}'")

        await asyncio.sleep(0.05)
        finished_at = datetime.now(timezone.utc)
        duration_ms = int((finished_at - started_at).total_seconds() * 1000)

        # Handle explicit mock scenario flags in command_str or workspace_path
        if "FAIL" in command_str.upper() or "FAIL" in workspace_path.upper():
            return SandboxResult(
                status=SandboxStatus.FAILED,
                exit_code=1,
                stdout=f"[MOCK_SANDBOX] Executing {command_str}\nRunning test suite...\nFAIL: 1 test failed.",
                stderr="AssertionError: Expected 200 OK but got 500 Internal Server Error",
                duration_ms=duration_ms,
                started_at=started_at,
                finished_at=finished_at,
                provider_type=self.provider_type.value,
                command_type=command_type.value,
                runtime=runtime,
                error_message="Validation suite failed with 1 error"
            )

        if "TIMEOUT" in command_str.upper() or "TIMEOUT" in workspace_path.upper():
            return SandboxResult(
                status=SandboxStatus.TIMED_OUT,
                exit_code=-1,
                stdout=f"[MOCK_SANDBOX] Executing {command_str}...",
                stderr=f"Task timed out after {timeout_seconds} seconds",
                duration_ms=timeout_seconds * 1000,
                started_at=started_at,
                finished_at=finished_at,
                provider_type=self.provider_type.value,
                command_type=command_type.value,
                runtime=runtime,
                error_message=f"Execution timed out after {timeout_seconds}s"
            )

        if "ERROR" in command_str.upper() or "ERROR" in workspace_path.upper():
            return SandboxResult(
                status=SandboxStatus.ERROR,
                exit_code=127,
                stdout="",
                stderr="Command not found or invalid runtime environment",
                duration_ms=duration_ms,
                started_at=started_at,
                finished_at=finished_at,
                provider_type=self.provider_type.value,
                command_type=command_type.value,
                runtime=runtime,
                error_message="Sandbox process initialization error"
            )

        # Default PASS scenario
        return SandboxResult(
            status=SandboxStatus.PASSED,
            exit_code=0,
            stdout=f"[MOCK_SANDBOX] Executing {command_str}...\nRunning validation suite for {runtime}\n5 passed in 0.05s",
            stderr="",
            duration_ms=duration_ms,
            started_at=started_at,
            finished_at=finished_at,
            provider_type=self.provider_type.value,
            command_type=command_type.value,
            runtime=runtime,
            error_message=None
        )
