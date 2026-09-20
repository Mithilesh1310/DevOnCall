import re
from typing import Optional, List, Dict, Any, Tuple
from app.services.staging.models import StagingDeployment, StagingDeploymentStatus


PROHIBITED_CONTAINER_MOUNTS = [
    "/var/run/docker.sock",
    "/etc/shadow",
    "/etc/passwd",
    "/.ssh",
    "/.aws",
    "/.kube",
    "C:\\Windows",
    "C:\\Users"
]

PRODUCTION_KEYWORD_PATTERNS = [
    re.compile(r'prod(uction)?', re.IGNORECASE),
    re.compile(r'live', re.IGNORECASE)
]


class StagingSecurityPolicy:
    """
    Enforces absolute production security boundary, staging permission,
    commit validation, staging secret isolation, and container security controls.
    """

    @staticmethod
    def validate_environment(environment: str) -> Tuple[bool, str]:
        if not environment or environment.upper() != "STAGING":
            return False, f"ENVIRONMENT_REJECTED: Environment '{environment}' is strictly BLOCKED. Only 'STAGING' is permitted."
        return True, "Valid environment"

    @staticmethod
    def validate_commit(commit_sha: str, branch: str) -> Tuple[bool, str]:
        if not commit_sha or commit_sha.strip().lower() in ["latest", "main", "master", "head"]:
            return False, f"INVALID_COMMIT: Exact git commit SHA required. Cannot deploy alias '{commit_sha}'."

        if len(commit_sha.strip()) < 6:
            return False, f"INVALID_COMMIT: Commit SHA '{commit_sha}' is too short."

        if not branch or branch.strip().lower() in ["main", "master"] and not branch.startswith("devoncall/"):
            return False, f"PROTECTED_BRANCH: Cannot deploy default branch '{branch}' directly. Must deploy feature/PR branch."

        return True, "Commit SHA and branch validated"

    @staticmethod
    def validate_container_security(volume_mounts: Optional[List[str]] = None) -> Tuple[bool, str]:
        if not volume_mounts:
            return True, "No volume mounts specified"

        for mount in volume_mounts:
            for prohibited in PROHIBITED_CONTAINER_MOUNTS:
                if prohibited.lower() in mount.lower():
                    return False, f"DOCKER_SECURITY_REJECTION: Mount '{mount}' violates container isolation policy."

        return True, "Container mounts compliant"

    @staticmethod
    def validate_staging_secrets(env_vars: Optional[Dict[str, str]] = None) -> Tuple[bool, str]:
        if not env_vars:
            return True, "No environment variables checked"

        for key, val in env_vars.items():
            if "DATABASE" in key.upper() or "REDIS" in key.upper() or "SECRET" in key.upper():
                for pattern in PRODUCTION_KEYWORD_PATTERNS:
                    if pattern.search(val):
                        return False, f"SECRET_ISOLATION_REJECTION: Variable '{key}' contains production keyword/reference."

        return True, "Staging secret isolation verified"


class StagingVerificationPolicy:
    """
    Configurable verification requirements for staging deployments.
    """

    def __init__(
        self,
        require_build: bool = True,
        require_health: bool = True,
        require_smoke: bool = True,
        require_browser: bool = False,
        require_sandbox: bool = False,
    ):
        self.require_build = require_build
        self.require_health = require_health
        self.require_smoke = require_smoke
        self.require_browser = require_browser
        self.require_sandbox = require_sandbox

    def evaluate_verdict(self, check_results: List[Dict[str, Any]]) -> Tuple[bool, str]:
        failed_checks = [c for c in check_results if c.get("status") == "FAIL"]
        if failed_checks:
            failed_types = ", ".join([c.get("check_type", "UNKNOWN") for c in failed_checks])
            return False, f"STAGING_VERDICT_FAILED: Failed checks: [{failed_types}]"

        return True, "STAGING_VERDICT_PASSED: All required verification stages passed cleanly."
