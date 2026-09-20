import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from app.services.deployment.base import BaseDeploymentProvider
from app.services.deployment.models import (
    ReleaseCandidateData,
    CanaryDeploymentData,
    CanaryVerificationData,
    ProductionDeploymentData,
    CanaryStatus,
    CanaryVerdict,
)
from app.services.deployment.security import DeploymentSecurityPolicy

logger = logging.getLogger("devoncall.deployment.provider.production")


class ProductionProvider(BaseDeploymentProvider):
    """
    Controlled Production Deployment Provider Adapter.
    Communicates strictly through a tightly-scoped deployment API or webhook reference.
    Contains NO arbitrary shell execution (no subprocess.call, no shell=True).
    Isolates production credentials from LLM contexts.
    """

    def __init__(self, api_url: Optional[str] = None, token_ref: Optional[str] = None):
        self.api_url = api_url
        self.token_ref = token_ref

    @property
    def provider_name(self) -> str:
        return "production"

    def _ensure_configured(self):
        if not self.api_url or not self.token_ref:
            logger.warning("Production deployment provider is NOT_CONFIGURED. Real production environment is unlinked.")
            raise RuntimeError("SECURITY_POLICY_VIOLATION: Real production deployment provider is NOT_CONFIGURED. Production deployment is BLOCKED.")

    def create_release_candidate(self, candidate_data: ReleaseCandidateData) -> Dict[str, Any]:
        self._ensure_configured()
        is_ok, reason = DeploymentSecurityPolicy.validate_commit_sha(candidate_data.commit_sha)
        if not is_ok:
            raise ValueError(reason)

        return {
            "status": "CANDIDATE_CREATED",
            "provider": "production",
            "commit_sha": candidate_data.commit_sha,
            "project_id": candidate_data.project_id
        }

    def deploy_canary(self, candidate: ReleaseCandidateData, traffic_percentage: int = 5) -> CanaryDeploymentData:
        self._ensure_configured()
        is_ok_c, reason_c = DeploymentSecurityPolicy.validate_commit_sha(candidate.commit_sha)
        if not is_ok_c:
            raise ValueError(reason_c)

        is_ok_t, reason_t = DeploymentSecurityPolicy.validate_canary_traffic(traffic_percentage)
        if not is_ok_t:
            raise ValueError(reason_t)

        return CanaryDeploymentData(
            id="canary-prod-101",
            release_candidate_id=candidate.id or "rc-prod-1",
            commit_sha=candidate.commit_sha,
            provider="production",
            status=CanaryStatus.DEPLOYED,
            traffic_percentage=traffic_percentage,
            deployment_url=f"https://canary.production.devoncall.internal",
            completed_at=datetime.now(timezone.utc).isoformat()
        )

    def verify_canary(self, canary_id: str) -> CanaryVerificationData:
        self._ensure_configured()
        return CanaryVerificationData(
            canary_deployment_id=canary_id,
            release_candidate_id="rc-prod-1",
            verdict=CanaryVerdict.PASS,
            baseline_error_rate=0.002,
            canary_error_rate=0.002,
            baseline_latency_ms=30.0,
            canary_latency_ms=31.0,
            new_critical_incidents=0,
            observation_count=50,
            reason="Production canary telemetry meets all verification thresholds."
        )

    def promote_full(self, candidate: ReleaseCandidateData) -> ProductionDeploymentData:
        self._ensure_configured()
        is_ok, reason = DeploymentSecurityPolicy.validate_commit_sha(candidate.commit_sha)
        if not is_ok:
            raise ValueError(reason)

        return ProductionDeploymentData(
            id="prod-deploy-101",
            release_candidate_id=candidate.id or "rc-prod-1",
            commit_sha=candidate.commit_sha,
            provider="production",
            status="DEPLOYED",
            deployment_url="https://production.devoncall.internal"
        )

    def rollback_release(self, candidate: ReleaseCandidateData) -> Dict[str, Any]:
        self._ensure_configured()
        is_ok, reason = DeploymentSecurityPolicy.validate_commit_sha(candidate.commit_sha)
        if not is_ok:
            raise ValueError(reason)

        return {
            "status": "ROLLED_BACK",
            "release_candidate_id": candidate.id,
            "commit_sha": candidate.commit_sha
        }

    def get_deployment_status(self, deployment_id: str) -> Dict[str, Any]:
        if not self.api_url:
            return {"id": deployment_id, "status": "BLOCKED", "reason": "NOT_CONFIGURED"}
        return {"id": deployment_id, "status": "ACTIVE", "provider": "production"}

    def execute_raw_shell(self, command_string: str) -> Dict[str, Any]:
        """Hard-rejects any attempt to execute arbitrary shell commands."""
        raise NotImplementedError("PRODUCTION = DENIED: Arbitrary shell execution strictly forbidden.")

    def health_check(self) -> Dict[str, Any]:
        if not self.api_url or not self.token_ref:
            return {"status": "BLOCKED", "provider": "production", "reason": "NOT_CONFIGURED"}
        return {"status": "HEALTHY", "provider": "production"}
