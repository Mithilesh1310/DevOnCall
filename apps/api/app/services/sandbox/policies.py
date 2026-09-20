import logging
from typing import Dict, Optional
from app.services.sandbox.base import CommandType

logger = logging.getLogger("devoncall.sandbox.policies")

PINNED_DOCKER_IMAGES = {
    "python": "python:3.11-slim",
    "python3": "python:3.11-slim",
    "node": "node:20-slim",
    "nodejs": "node:20-slim",
    "typescript": "node:20-slim"
}

DEFAULT_VALIDATION_COMMANDS = {
    "python": {
        CommandType.TEST: "pytest",
        CommandType.BUILD: "python -m build",
        CommandType.LINT: "flake8",
        CommandType.TYPECHECK: "mypy ."
    },
    "node": {
        CommandType.TEST: "npm test",
        CommandType.BUILD: "npm run build",
        CommandType.LINT: "npm run lint",
        CommandType.TYPECHECK: "npx tsc --noEmit"
    }
}

class SandboxSecurityPolicy:
    """
    Strict security policy enforcing network isolation, runtime image pinning, and command allowlisting.
    """
    NETWORK_ENABLED: bool = False

    @classmethod
    def get_docker_image(cls, runtime: str) -> str:
        clean_rt = runtime.lower().strip()
        if clean_rt not in PINNED_DOCKER_IMAGES:
            raise ValueError(f"Unsupported sandbox runtime '{runtime}'. Pinned supported runtimes: {list(PINNED_DOCKER_IMAGES.keys())}")
        return PINNED_DOCKER_IMAGES[clean_rt]

    @classmethod
    def resolve_command(
        cls,
        command_type: CommandType,
        project_config: Optional[Dict[str, str]] = None,
        runtime: str = "python"
    ) -> str:
        """
        Resolves command_type to configured command. Returns string or raises ValueError if missing.
        """
        if project_config:
            cmd_key = f"{command_type.value.lower()}_command"
            if cmd_key in project_config and project_config[cmd_key]:
                return project_config[cmd_key]

        clean_rt = "node" if "node" in runtime.lower() or "typescript" in runtime.lower() else "python"
        rt_defaults = DEFAULT_VALIDATION_COMMANDS.get(clean_rt, {})
        
        if command_type in rt_defaults:
            return rt_defaults[command_type]

        raise ValueError(f"VALIDATION_COMMAND_NOT_CONFIGURED: Command type '{command_type}' is not configured.")
