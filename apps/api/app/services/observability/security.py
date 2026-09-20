import logging
from enum import Enum
from typing import Dict, Any, Tuple

logger = logging.getLogger("devoncall.observability.security")


class ForbiddenProductionOperation(str, Enum):
    PRODUCTION_SHELL = "PRODUCTION_SHELL"
    PRODUCTION_FS_WRITE = "PRODUCTION_FS_WRITE"
    PRODUCTION_DB_WRITE = "PRODUCTION_DB_WRITE"
    PRODUCTION_RESTART = "PRODUCTION_RESTART"
    PRODUCTION_DEPLOY = "PRODUCTION_DEPLOY"
    PRODUCTION_ROLLBACK = "PRODUCTION_ROLLBACK"
    PRODUCTION_ENV_MODIFY = "PRODUCTION_ENV_MODIFY"
    PRODUCTION_CREDENTIAL_ACCESS = "PRODUCTION_CREDENTIAL_ACCESS"


class ProductionSafetyPolicy:
    """
    Enforces absolute READ_ONLY production security boundaries.
    Hard-rejects any attempt to execute production shell commands, filesystem writes,
    database mutations, service restarts, production deployments, or rollbacks.
    """

    ALLOWED_READ_ONLY_OPERATIONS = {
        "RECEIVE_TELEMETRY",
        "INSPECT_INCIDENT",
        "CORRELATE_COMMIT",
        "INSPECT_REPOSITORY",
        "QUERY_PROJECT_BRAIN",
        "INVESTIGATE_ROOT_CAUSE",
        "PROPOSE_REMEDIATION",
        "CREATE_PHASE3_WORKSPACE",
        "RUN_SANDBOX_VALIDATION",
        "RUN_BROWSER_VERIFICATION",
        "DEPLOY_TO_STAGING",
        "REQUEST_HUMAN_APPROVAL",
    }

    FORBIDDEN_OPERATIONS = {
        ForbiddenProductionOperation.PRODUCTION_SHELL: "Direct shell execution on production hosts is forbidden.",
        ForbiddenProductionOperation.PRODUCTION_FS_WRITE: "Filesystem modifications to production servers are forbidden.",
        ForbiddenProductionOperation.PRODUCTION_DB_WRITE: "Autonomous database writes or schema mutations on production are forbidden.",
        ForbiddenProductionOperation.PRODUCTION_RESTART: "Restarting production application containers or services is forbidden.",
        ForbiddenProductionOperation.PRODUCTION_DEPLOY: "Direct production deployments are forbidden. Use Phase 9 Staging and PR workflow.",
        ForbiddenProductionOperation.PRODUCTION_ROLLBACK: "Autonomous production rollbacks are forbidden.",
        ForbiddenProductionOperation.PRODUCTION_ENV_MODIFY: "Modifying production environment variables or secrets is forbidden.",
        ForbiddenProductionOperation.PRODUCTION_CREDENTIAL_ACCESS: "Accessing production root credentials or private keys is forbidden.",
    }

    @classmethod
    def validate_action(cls, action_name: str, environment: str = "PRODUCTION") -> Tuple[bool, str]:
        """
        Validates whether an action is permitted within the Production READ_ONLY safety boundary.
        Returns (is_allowed, reason).
        """
        env_upper = (environment or "PRODUCTION").upper()
        act_upper = action_name.upper().strip()

        # Check explicit forbidden operations
        for op, reason in cls.FORBIDDEN_OPERATIONS.items():
            if act_upper == op.value or op.value in act_upper:
                logger.warning(f"SECURITY_POLICY_VIOLATION: Denied forbidden operation '{act_upper}' in environment '{env_upper}'.")
                return False, f"SECURITY_POLICY_VIOLATION: {reason}"

        # If targeting production, verify action is in allowed read-only list
        if env_upper == "PRODUCTION":
            if act_upper not in cls.ALLOWED_READ_ONLY_OPERATIONS:
                # Check keywords like shell, deploy, rollback, restart, write
                if any(w in act_upper for w in ["SHELL", "DEPLOY", "ROLLBACK", "RESTART", "WRITE", "DELETE", "DROP"]):
                    logger.warning(f"SECURITY_POLICY_VIOLATION: Action '{act_upper}' violates PRODUCTION READ_ONLY boundary.")
                    return False, f"SECURITY_POLICY_VIOLATION: Action '{act_upper}' is forbidden on production environments."

        return True, "ALLOWED"
