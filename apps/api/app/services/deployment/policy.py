import logging
from typing import Tuple, Optional, Dict, Any
from app.services.deployment.models import ReleaseCandidateData, ReleaseCandidateStatus
from app.services.deployment.security import DeploymentSecurityPolicy

logger = logging.getLogger("devoncall.deployment.policy")


class ReleaseCandidatePolicy:
    """
    Evaluates whether a release candidate meets all prerequisites to advance through
    the production release state machine.
    """

    @classmethod
    def can_request_approval(cls, candidate: ReleaseCandidateData) -> Tuple[bool, str]:
        # 1. Exact Commit SHA Check
        is_ok, reason = DeploymentSecurityPolicy.validate_commit_sha(candidate.commit_sha)
        if not is_ok:
            return False, reason

        # 2. PR Exists
        if not candidate.pull_request_id:
            return False, "RELEASE_POLICY_VIOLATION: Pull Request reference is required."

        # 3. Staging Deployment Passed
        if (candidate.staging_verification_status or "").upper() != "PASSED":
            return False, f"RELEASE_POLICY_VIOLATION: Staging verification status is '{candidate.staging_verification_status}'. Must be 'PASSED'."

        # 4. Browser Verification Passed
        if (candidate.browser_verification_status or "").upper() != "PASSED":
            return False, f"RELEASE_POLICY_VIOLATION: Browser verification status is '{candidate.browser_verification_status}'. Must be 'PASSED'."

        return True, "PREREQUISITES_PASSED"

    @classmethod
    def can_deploy_canary(cls, candidate: ReleaseCandidateData, is_approved: bool, traffic_percentage: int = 5) -> Tuple[bool, str]:
        # Check prerequisites
        can_req, req_reason = cls.can_request_approval(candidate)
        if not can_req:
            return False, req_reason

        # Approval check
        if not is_approved:
            return False, "RELEASE_POLICY_VIOLATION: Explicit human approval for STAGING_TO_CANARY is required."

        # Traffic percentage check
        can_t, t_reason = DeploymentSecurityPolicy.validate_canary_traffic(traffic_percentage)
        if not can_t:
            return False, t_reason

        return True, "CANARY_DEPLOYMENT_PERMITTED"

    @classmethod
    def can_promote_full(cls, candidate: ReleaseCandidateData, is_canary_passed: bool, is_full_approved: bool) -> Tuple[bool, str]:
        is_ok, reason = DeploymentSecurityPolicy.validate_commit_sha(candidate.commit_sha)
        if not is_ok:
            return False, reason

        if not is_canary_passed:
            return False, "RELEASE_POLICY_VIOLATION: Canary verification MUST pass before promoting to full production."

        if not is_full_approved:
            return False, "RELEASE_POLICY_VIOLATION: Explicit human approval for CANARY_TO_FULL_PRODUCTION is required."

        return True, "FULL_PROMOTION_PERMITTED"
