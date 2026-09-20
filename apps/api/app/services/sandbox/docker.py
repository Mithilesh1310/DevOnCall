import asyncio
import logging
import shutil
from datetime import datetime, timezone
from app.services.sandbox.base import BaseSandboxProvider, CommandType, SandboxProviderType, SandboxStatus
from app.services.sandbox.result import SandboxResult
from app.services.sandbox.policies import SandboxSecurityPolicy

logger = logging.getLogger("devoncall.sandbox.docker")

class DockerSandboxProvider(BaseSandboxProvider):
    """
    Production-grade Docker Sandbox Provider using CLI/container runtime isolation.
    If Docker is not installed/running, returns DOCKER_UNAVAILABLE / SANDBOX_BLOCKED cleanly.
    """

    @property
    def provider_type(self) -> SandboxProviderType:
        return SandboxProviderType.DOCKER_SANDBOX

    async def is_available(self) -> bool:
        """
        Checks if docker executable is in PATH and daemon is reachable.
        """
        if not shutil.which("docker"):
            return False
        
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "info",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, _ = await proc.communicate()
            return proc.returncode == 0
        except Exception as e:
            logger.debug(f"Docker availability check failed: {e}")
            return False

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

        if not await self.is_available():
            logger.warning("Docker CLI/Daemon is unavailable on host system. Returning SANDBOX_BLOCKED.")
            finished_at = datetime.now(timezone.utc)
            return SandboxResult(
                status=SandboxStatus.BLOCKED,
                exit_code=-1,
                stdout="",
                stderr="DOCKER_UNAVAILABLE: Docker daemon or CLI is not installed or running on host system.",
                duration_ms=int((finished_at - started_at).total_seconds() * 1000),
                started_at=started_at,
                finished_at=finished_at,
                provider_type=self.provider_type.value,
                command_type=command_type.value,
                runtime=runtime,
                error_message="Docker runtime unavailable"
            )

        # Get pinned image name
        try:
            image_name = SandboxSecurityPolicy.get_docker_image(runtime)
        except ValueError as ve:
            finished_at = datetime.now(timezone.utc)
            return SandboxResult(
                status=SandboxStatus.ERROR,
                exit_code=-1,
                stdout="",
                stderr=str(ve),
                duration_ms=int((finished_at - started_at).total_seconds() * 1000),
                started_at=started_at,
                finished_at=finished_at,
                provider_type=self.provider_type.value,
                command_type=command_type.value,
                runtime=runtime,
                error_message=str(ve)
            )

        # Build Docker run command with strict security flags:
        # --rm: ephemeral, remove container upon exit
        # --network none: network disabled
        # --cpus: CPU limit
        # --memory: Memory limit
        # -v: mount workspace path only into /workspace
        # -w: set working directory /workspace
        docker_cmd = [
            "docker", "run", "--rm",
            "--network", "none",
            "--cpus", str(cpu_limit),
            "--memory", memory_limit,
            "-v", f"{workspace_path}:/workspace:rw",
            "-w", "/workspace",
            image_name,
            "sh", "-c", command_str
        ]

        logger.info(f"[DOCKER_SANDBOX] Spawning container with command: {' '.join(docker_cmd)}")

        try:
            proc = await asyncio.create_subprocess_exec(
                *docker_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout_data, stderr_data = await asyncio.wait_for(proc.communicate(), timeout=float(timeout_seconds))
                finished_at = datetime.now(timezone.utc)
                duration_ms = int((finished_at - started_at).total_seconds() * 1000)

                stdout_str = stdout_data.decode("utf-8", errors="replace")[:max_output_bytes]
                stderr_str = stderr_data.decode("utf-8", errors="replace")[:max_output_bytes]

                status = SandboxStatus.PASSED if proc.returncode == 0 else SandboxStatus.FAILED

                return SandboxResult(
                    status=status,
                    exit_code=proc.returncode,
                    stdout=stdout_str,
                    stderr=stderr_str,
                    duration_ms=duration_ms,
                    started_at=started_at,
                    finished_at=finished_at,
                    provider_type=self.provider_type.value,
                    command_type=command_type.value,
                    runtime=runtime,
                    error_message=None if status == SandboxStatus.PASSED else f"Exit code {proc.returncode}"
                )

            except asyncio.TimeoutError:
                finished_at = datetime.now(timezone.utc)
                try:
                    proc.kill()
                except Exception:
                    pass
                return SandboxResult(
                    status=SandboxStatus.TIMED_OUT,
                    exit_code=-1,
                    stdout="",
                    stderr=f"Execution timed out after {timeout_seconds} seconds",
                    duration_ms=timeout_seconds * 1000,
                    started_at=started_at,
                    finished_at=finished_at,
                    provider_type=self.provider_type.value,
                    command_type=command_type.value,
                    runtime=runtime,
                    error_message=f"Timeout after {timeout_seconds}s"
                )

        except Exception as ex:
            finished_at = datetime.now(timezone.utc)
            logger.error(f"[DOCKER_SANDBOX] Container execution exception: {ex}")
            return SandboxResult(
                status=SandboxStatus.ERROR,
                exit_code=-1,
                stdout="",
                stderr=f"Container creation error: {str(ex)}",
                duration_ms=int((finished_at - started_at).total_seconds() * 1000),
                started_at=started_at,
                finished_at=finished_at,
                provider_type=self.provider_type.value,
                command_type=command_type.value,
                runtime=runtime,
                error_message=str(ex)
            )
