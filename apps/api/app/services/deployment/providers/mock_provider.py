import uuid
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


class MockDeploymentProvider(BaseDeploymentProvider):
    """
    Deterministic Mock Deployment Provider for local development and offline testing.
    Supports scenarios: STAGING_PASS, CANARY_DEPLOY_PASS, CANARY_HEALTH_FAIL, CANARY_ERROR_RATE_HIGH,
    CANARY_LATENCY_HIGH, CANARY_CRITICAL_INCIDENT, CANARY_INSUFFICIENT_DATA, CANARY_HUMAN_REVIEW,
    FULL_DEPLOY_PASS, FULL_DEPLOY_FAIL, ROLLBACK_PASS, ROLLBACK_FAIL.
    """

    def __init__(self, scenario: str = "CANARY_DEPLOY_PASS"):
        self.scenario = scenario.upper()

    @property
    def provider_name(self) -> str:
        return "mock"

    def create_release_candidate(self, candidate_data: ReleaseCandidateData) -> Dict[str, Any]:
        is_ok, reason = DeploymentSecurityPolicy.validate_commit_sha(candidate_data.commit_sha)
        if not is_ok:
            raise ValueError(reason)

        return {
            "status": "CANDIDATE_CREATED",
            "provider": "mock",
            "commit_sha": candidate_data.commit_sha,
            "project_id": candidate_data.project_id
        }

    def deploy_canary(self, candidate: ReleaseCandidateData, traffic_percentage: int = 5) -> CanaryDeploymentData:
        is_ok_c, reason_c = DeploymentSecurityPolicy.validate_commit_sha(candidate.commit_sha)
        if not is_ok_c:
            raise ValueError(reason_c)

        is_ok_t, reason_t = DeploymentSecurityPolicy.validate_canary_traffic(traffic_percentage)
        if not is_ok_t:
            raise ValueError(reason_t)

        canary_id = f"canary-{uuid.uuid4().hex[:8]}"

        if self.scenario == "FULL_DEPLOY_FAIL":
            return CanaryDeploymentData(
                id=canary_id,
                release_candidate_id=candidate.id or "rc-demo-1",
                commit_sha=candidate.commit_sha,
                provider="mock",
                status=CanaryStatus.FAILED,
                traffic_percentage=traffic_percentage,
                error="Mock Canary deployment failed during container bootstrap.",
                completed_at=datetime.now(timezone.utc).isoformat()
            )

        return CanaryDeploymentData(
            id=canary_id,
            release_candidate_id=candidate.id or "rc-demo-1",
            commit_sha=candidate.commit_sha,
            provider="mock",
            status=CanaryStatus.DEPLOYED,
            traffic_percentage=traffic_percentage,
            deployment_url=f"http://127.0.0.1:3099/canary/{canary_id[:6]}",
            completed_at=datetime.now(timezone.utc).isoformat()
        )

    def verify_canary(self, canary_id: str) -> CanaryVerificationData:
        if self.scenario == "CANARY_HEALTH_FAIL":
            return CanaryVerificationData(
                canary_deployment_id=canary_id,
                release_candidate_id="rc-demo-1",
                verdict=CanaryVerdict.FAIL,
                baseline_error_rate=0.005,
                canary_error_rate=0.08,
                baseline_latency_ms=45.0,
                canary_latency_ms=45.0,
                new_critical_incidents=0,
                observation_count=25,
                reason="Canary health check failed: HTTP 500 error on /health endpoint."
            )
        elif self.scenario == "CANARY_ERROR_RATE_HIGH":
            return CanaryVerificationData(
                canary_deployment_id=canary_id,
                release_candidate_id="rc-demo-1",
                verdict=CanaryVerdict.FAIL,
                baseline_error_rate=0.005,
                canary_error_rate=0.045,
                baseline_latency_ms=45.0,
                canary_latency_ms=50.0,
                new_critical_incidents=0,
                observation_count=30,
                reason="Canary error rate (4.5%) exceeded maximum threshold (2.0%)."
            )
        elif self.scenario == "CANARY_LATENCY_HIGH":
            return CanaryVerificationData(
                canary_deployment_id=canary_id,
                release_candidate_id="rc-demo-1",
                verdict=CanaryVerdict.FAIL,
                baseline_error_rate=0.005,
                canary_error_rate=0.006,
                baseline_latency_ms=45.0,
                canary_latency_ms=95.0,
                new_critical_incidents=0,
                observation_count=25,
                reason="Canary latency multiplier (2.1x) exceeded maximum threshold (1.5x)."
            )
        elif self.scenario == "CANARY_CRITICAL_INCIDENT":
            return CanaryVerificationData(
                canary_deployment_id=canary_id,
                release_candidate_id="rc-demo-1",
                verdict=CanaryVerdict.FAIL,
                baseline_error_rate=0.005,
                canary_error_rate=0.01,
                baseline_latency_ms=45.0,
                canary_latency_ms=50.0,
                new_critical_incidents=2,
                observation_count=25,
                reason="New critical production incident detected during canary observation window."
            )
        elif self.scenario == "CANARY_INSUFFICIENT_DATA":
            return CanaryVerificationData(
                canary_deployment_id=canary_id,
                release_candidate_id="rc-demo-1",
                verdict=CanaryVerdict.INSUFFICIENT_DATA,
                baseline_error_rate=0.005,
                canary_error_rate=0.0,
                baseline_latency_ms=45.0,
                canary_latency_ms=45.0,
                new_critical_incidents=0,
                observation_count=3,
                reason="Telemetry observation count (3) is below minimum required threshold (20)."
            )
        elif self.scenario == "CANARY_HUMAN_REVIEW":
            return CanaryVerificationData(
                canary_deployment_id=canary_id,
                release_candidate_id="rc-demo-1",
                verdict=CanaryVerdict.HUMAN_REVIEW,
                baseline_error_rate=0.005,
                canary_error_rate=0.018,
                baseline_latency_ms=45.0,
                canary_latency_ms=65.0,
                new_critical_incidents=0,
                observation_count=22,
                reason="Conflicting telemetry signals detected: Error rate near threshold."
            )

        # Default PASS scenario
        return CanaryVerificationData(
            canary_deployment_id=canary_id,
            release_candidate_id="rc-demo-1",
            verdict=CanaryVerdict.PASS,
            baseline_error_rate=0.005,
            canary_error_rate=0.006,
            baseline_latency_ms=45.0,
            canary_latency_ms=48.0,
            new_critical_incidents=0,
            observation_count=35,
            reason="Canary telemetry meets all verification thresholds."
        )

    def promote_full(self, candidate: ReleaseCandidateData) -> ProductionDeploymentData:
        is_ok, reason = DeploymentSecurityPolicy.validate_commit_sha(candidate.commit_sha)
        if not is_ok:
            raise ValueError(reason)

        if self.scenario == "FULL_DEPLOY_FAIL":
            raise RuntimeError("Mock full production promotion failed.")

        return ProductionDeploymentData(
            id=f"prod-{uuid.uuid4().hex[:8]}",
            release_candidate_id=candidate.id or "rc-demo-1",
            commit_sha=candidate.commit_sha,
            provider="mock",
            status="DEPLOYED",
            deployment_url="http://127.0.0.1:3000"
        )

    def rollback_release(self, candidate: ReleaseCandidateData) -> Dict[str, Any]:
        is_ok, reason = DeploymentSecurityPolicy.validate_commit_sha(candidate.commit_sha)
        if not is_ok:
            raise ValueError(reason)

        if self.scenario == "ROLLBACK_FAIL":
            return {
                "status": "ROLLBACK_FAILED",
                "release_candidate_id": candidate.id,
                "commit_sha": candidate.commit_sha,
                "error": "Mock rollback failed to restore previous version."
            }

        return {
            "status": "ROLLED_BACK",
            "release_candidate_id": candidate.id,
            "commit_sha": candidate.commit_sha,
            "previous_stable_commit": "a0b1c2d3e4f5"
        }

    def get_deployment_status(self, deployment_id: str) -> Dict[str, Any]:
        return {"id": deployment_id, "status": "HEALTHY", "provider": "mock"}

    def health_check(self) -> Dict[str, Any]:
        return {"status": "HEALTHY", "provider": "mock", "scenario": self.scenario}
