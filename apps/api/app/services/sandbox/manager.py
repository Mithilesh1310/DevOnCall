import logging
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.sandbox.base import BaseSandboxProvider, CommandType, SandboxProviderType, SandboxStatus
from app.services.sandbox.result import SandboxResult
from app.services.sandbox.limits import default_sandbox_limits
from app.services.sandbox.policies import SandboxSecurityPolicy
from app.services.sandbox.mock_provider import MockSandboxProvider
from app.services.sandbox.docker import DockerSandboxProvider
from app.services.agent.policies import AgentPolicy, ToolPermission
from app.models.sandbox_run import SandboxRun

logger = logging.getLogger("devoncall.sandbox.manager")

class SandboxManager:
    """
    Central orchestrator for Phase 5 Sandbox Validation runs.
    """

    def __init__(self, provider: Optional[BaseSandboxProvider] = None):
        self.docker_provider = DockerSandboxProvider()
        self.mock_provider = MockSandboxProvider()
        self.custom_provider = provider

    async def run_validation(
        self,
        db: AsyncSession,
        project_id: str,
        workspace_id: str,
        workspace_path: str,
        command_type: CommandType,
        agent_run_id: Optional[str] = None,
        runtime: str = "python",
        project_config: Optional[Dict[str, str]] = None,
        policy: Optional[AgentPolicy] = None,
        force_mock: bool = False
    ) -> SandboxRun:
        # 1. Enforce Permission Check
        if policy and not policy.is_permission_allowed(ToolPermission.EXECUTE_SANDBOX):
            logger.warning(f"Permission DENIED: Policy rejects {ToolPermission.EXECUTE_SANDBOX}")
            raise PermissionError("Permission DENIED: EXECUTE_SANDBOX permission is required for sandbox validation")

        # 2. Resolve Command Allowlist
        command_str = SandboxSecurityPolicy.resolve_command(
            command_type=command_type,
            project_config=project_config,
            runtime=runtime
        )

        import os
        test_mode = os.getenv("TEST_MODE", "false").lower() in ["true", "1", "yes"]

        # 3. Select Provider (Custom / Force Mock / Docker / Explicit Failure)
        if self.custom_provider:
            active_provider = self.custom_provider
        elif force_mock or test_mode:
            active_provider = self.mock_provider
        else:
            if await self.docker_provider.is_available():
                active_provider = self.docker_provider
            else:
                logger.error("DOCKER = BLOCKED: Docker daemon unavailable in runtime.")
                raise RuntimeError("DOCKER = BLOCKED: Docker daemon is not running and TEST_MODE is disabled.")

        logger.info(
            f"sandbox_started sandbox_run_id='pending' agent_run_id='{agent_run_id}' workspace_id='{workspace_id}' "
            f"project_id='{project_id}' provider='{active_provider.provider_type.value}' command='{command_type.value}'"
        )

        # 4. Execute Validation Run
        result: SandboxResult = await active_provider.run_validation(
            workspace_path=workspace_path,
            command_type=command_type,
            command_str=command_str,
            runtime=runtime,
            timeout_seconds=default_sandbox_limits.timeout_seconds,
            cpu_limit=default_sandbox_limits.cpu_limit,
            memory_limit=default_sandbox_limits.memory_limit,
            max_output_bytes=default_sandbox_limits.max_output_bytes
        )

        logger.info(
            f"sandbox_command_completed status='{result.status}' exit_code={result.exit_code} "
            f"duration_ms={result.duration_ms} provider='{result.provider_type}'"
        )

        # 5. Persist SandboxRun Model in Database
        sandbox_run = SandboxRun(
            project_id=project_id,
            agent_run_id=agent_run_id,
            workspace_id=workspace_id,
            command_type=command_type.value,
            runtime=runtime,
            provider_type=result.provider_type,
            status=result.status,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            duration_ms=result.duration_ms,
            started_at=result.started_at,
            finished_at=result.finished_at,
            timeout_seconds=default_sandbox_limits.timeout_seconds,
            resource_limits={
                "cpu_limit": default_sandbox_limits.cpu_limit,
                "memory_limit": default_sandbox_limits.memory_limit,
                "max_output_bytes": default_sandbox_limits.max_output_bytes
            },
            error_message=result.error_message
        )
        db.add(sandbox_run)
        await db.commit()
        await db.refresh(sandbox_run)

        return sandbox_run
