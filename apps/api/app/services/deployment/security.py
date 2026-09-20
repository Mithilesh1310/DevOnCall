import re
import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Tuple, Dict, Any, Optional
from app.services.brain.provenance import BrainSecretRedactor

logger = logging.getLogger("devoncall.deployment.security")


class DeploymentSecurityPolicy:
    """
    Enforces strict security rules for Phase 12 Controlled Canary Deployments:
    1. Exact 40-character commit SHA required (rejects 'latest', 'main', 'master', floating tags).
    2. Canary traffic percentage strictly bounded between 1% and 10% (rejects 100% canary).
    3. Production credentials isolated — never stored in Brain, AgentState, WhatsApp, or LLM prompts.
    4. Subprocess arbitrary shell execution strictly FORBIDDEN.
    5. Double Human Approval required.
    """

    FLOATING_TAGS = {"latest", "main", "master", "develop", "head", "latest-release"}

    @classmethod
    def validate_commit_sha(cls, commit_sha: Optional[str]) -> Tuple[bool, str]:
        if not commit_sha or not isinstance(commit_sha, str):
            return False, "SECURITY_POLICY_VIOLATION: Commit SHA must be provided."

        commit_clean = commit_sha.strip().lower()

        if commit_clean in cls.FLOATING_TAGS or len(commit_clean) < 7:
            return False, f"SECURITY_POLICY_VIOLATION: Floating tag or branch reference '{commit_sha}' rejected. Exact 40-character commit SHA required."

        # Verify hex format & 40 char hex requirement for strict production candidates
        if not re.match(r'^[0-9a-fA-F]{40}$', commit_clean):
            return False, f"SECURITY_POLICY_VIOLATION: Commit SHA '{commit_sha}' MUST be an exact 40-character hexadecimal hash."

        return True, "SHA_VALID"

    @classmethod
    def validate_canary_traffic(cls, percentage: float) -> Tuple[bool, str]:
        if percentage < 1.0 or percentage > 10.0:
            return False, f"SECURITY_POLICY_VIOLATION: Canary traffic percentage ({percentage}%) MUST be between 1.0% and 10.0%. (100% canary is rejected)."
        return True, "VALID_CANARY_TRAFFIC"

    @classmethod
    def generate_confirmation_token(cls, rc_id: str, approval_type: Any) -> Tuple[str, float]:
        """Generates a short-lived single-use confirmation token."""
        token = f"TOK-{secrets.token_hex(8).upper()}"
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).timestamp()
        return token, expires_at

    @classmethod
    def scrub_credentials(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Scrubs production secrets or deployment tokens from output dictionaries."""
        return BrainSecretRedactor.redact_dict(data)

    @classmethod
    def validate_shell_execution(cls, command_string: str) -> Tuple[bool, str]:
        """Hard-rejects any attempt to run arbitrary shell commands."""
        logger.warning(f"SECURITY_POLICY_VIOLATION: Attempted arbitrary shell command '{command_string}' in deployment service.")
        return False, "SECURITY_POLICY_VIOLATION: Arbitrary shell execution is strictly FORBIDDEN in deployment provider."
