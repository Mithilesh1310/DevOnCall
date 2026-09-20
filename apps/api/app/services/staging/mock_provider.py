from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from app.services.staging.base import BaseStagingProvider
from app.services.staging.models import (
    StagingDeployment,
    StagingDeploymentStatus,
    StagingCheckResult,
    StagingCheckType,
    StagingCheckStatus,
)


class MockStagingProvider(BaseStagingProvider):
    """
    Deterministic Mock Staging Provider for testing DevOnCall staging lifecycle offline.
    """

    def __init__(self, scenario: str = "PASS"):
        self.scenario = scenario
        self.active_deployments: Dict[str, StagingDeployment] = {}

    @property
    def provider_name(self) -> str:
        return "MOCK_STAGING"

    @property
    def is_available(self) -> bool:
        return True

    async def deploy_staging(self, deployment: StagingDeployment) -> StagingDeployment:
        deployment.provider = self.provider_name
        deployment.started_at = datetime.now(timezone.utc).isoformat()
        deployment.checks = []

        if self.scenario == "BUILD_FAIL":
            deployment.status = StagingDeploymentStatus.FAILED
            deployment.error_type = "BUILD_ERROR"
            deployment.error_message = "Mock build failed: TypeScript compilation error in src/index.ts"
            deployment.checks.append(
                StagingCheckResult(
                    deployment_id=deployment.id,
                    check_type=StagingCheckType.BUILD,
                    status=StagingCheckStatus.FAIL,
                    duration_ms=1200,
                    summary="Build failed: TS2322 Type error",
                    details={"error": "Type 'string' is not assignable to type 'number'."},
                )
            )
            deployment.finished_at = datetime.now(timezone.utc).isoformat()
            self.active_deployments[deployment.id] = deployment
            return deployment

        # 1. BUILD PASS
        deployment.checks.append(
            StagingCheckResult(
                deployment_id=deployment.id,
                check_type=StagingCheckType.BUILD,
                status=StagingCheckStatus.PASS,
                duration_ms=2500,
                summary="Build succeeded cleanly via Sandbox environment",
                details={"artifacts": ["dist/app.js", "dist/styles.css"]},
            )
        )

        if self.scenario == "DEPLOY_FAIL":
            deployment.status = StagingDeploymentStatus.FAILED
            deployment.error_type = "DEPLOYMENT_ERROR"
            deployment.error_message = "Mock deploy failed: Port allocation conflict"
            deployment.checks.append(
                StagingCheckResult(
                    deployment_id=deployment.id,
                    check_type=StagingCheckType.DEPLOYMENT,
                    status=StagingCheckStatus.FAIL,
                    duration_ms=800,
                    summary="Deployment failed: Container failed to start",
                )
            )
            deployment.finished_at = datetime.now(timezone.utc).isoformat()
            self.active_deployments[deployment.id] = deployment
            return deployment

        # 2. DEPLOY PASS
        deployment.deployment_url = f"http://127.0.0.1:3099/{deployment.id[:8]}"
        deployment.checks.append(
            StagingCheckResult(
                deployment_id=deployment.id,
                check_type=StagingCheckType.DEPLOYMENT,
                status=StagingCheckStatus.PASS,
                duration_ms=1500,
                summary=f"Staging environment deployed at {deployment.deployment_url}",
                details={"network": f"staging-net-{deployment.id[:8]}", "port": 3099},
            )
        )

        if self.scenario == "HEALTH_FAIL":
            deployment.status = StagingDeploymentStatus.FAILED
            deployment.error_type = "HEALTH_CHECK_FAILED"
            deployment.error_message = "Mock health check failed: HTTP 500 Server Error on /health"
            deployment.health_status = "UNHEALTHY"
            deployment.checks.append(
                StagingCheckResult(
                    deployment_id=deployment.id,
                    check_type=StagingCheckType.HEALTH,
                    status=StagingCheckStatus.FAIL,
                    duration_ms=5000,
                    summary="Health check failed: HTTP 500 on GET /health",
                )
            )
            deployment.finished_at = datetime.now(timezone.utc).isoformat()
            self.active_deployments[deployment.id] = deployment
            return deployment

        # 3. HEALTH PASS
        deployment.health_status = "HEALTHY"
        deployment.checks.append(
            StagingCheckResult(
                deployment_id=deployment.id,
                check_type=StagingCheckType.HEALTH,
                status=StagingCheckStatus.PASS,
                duration_ms=350,
                summary="Health check passed: GET /health HTTP 200 OK (response_time: 45ms)",
                details={"http_status": 200, "response_time_ms": 45},
            )
        )

        if self.scenario == "SMOKE_FAIL":
            deployment.status = StagingDeploymentStatus.FAILED
            deployment.error_type = "SMOKE_TEST_FAILED"
            deployment.error_message = "Mock smoke test failed: GET /api/users returned HTTP 502 Bad Gateway"
            deployment.checks.append(
                StagingCheckResult(
                    deployment_id=deployment.id,
                    check_type=StagingCheckType.SMOKE,
                    status=StagingCheckStatus.FAIL,
                    duration_ms=1100,
                    summary="Smoke test failed: GET /api/users returned 502",
                )
            )
            deployment.finished_at = datetime.now(timezone.utc).isoformat()
            self.active_deployments[deployment.id] = deployment
            return deployment

        # 4. SMOKE PASS
        deployment.checks.append(
            StagingCheckResult(
                deployment_id=deployment.id,
                check_type=StagingCheckType.SMOKE,
                status=StagingCheckStatus.PASS,
                duration_ms=620,
                summary="Smoke tests passed: GET / and GET /health responded HTTP 200 OK",
                details={"tested_endpoints": ["/", "/health", "/api/health"]},
            )
        )

        if self.scenario == "BROWSER_FAIL":
            deployment.status = StagingDeploymentStatus.FAILED
            deployment.error_type = "BROWSER_VERIFICATION_FAILED"
            deployment.error_message = "Mock browser test failed: Button #submit-btn not found"
            deployment.checks.append(
                StagingCheckResult(
                    deployment_id=deployment.id,
                    check_type=StagingCheckType.BROWSER,
                    status=StagingCheckStatus.FAIL,
                    duration_ms=3200,
                    summary="Playwright UI verification failed: Selector #submit-btn element not found",
                )
            )
            deployment.finished_at = datetime.now(timezone.utc).isoformat()
            self.active_deployments[deployment.id] = deployment
            return deployment

        # 5. BROWSER PASS
        deployment.checks.append(
            StagingCheckResult(
                deployment_id=deployment.id,
                check_type=StagingCheckType.BROWSER,
                status=StagingCheckStatus.PASS,
                duration_ms=4100,
                summary="Playwright UI verification passed: Scenario 'login-smoke' executed successfully",
                details={"steps_passed": 5, "screenshots_taken": 2},
            )
        )

        deployment.status = StagingDeploymentStatus.PASSED
        deployment.duration_ms = 10370
        deployment.finished_at = datetime.now(timezone.utc).isoformat()
        self.active_deployments[deployment.id] = deployment
        return deployment

    async def health_check(self, deployment: StagingDeployment) -> StagingCheckResult:
        if deployment.health_status == "HEALTHY":
            return StagingCheckResult(
                deployment_id=deployment.id,
                check_type=StagingCheckType.HEALTH,
                status=StagingCheckStatus.PASS,
                duration_ms=120,
                summary="Health check passed (GET /health HTTP 200)",
            )
        return StagingCheckResult(
            deployment_id=deployment.id,
            check_type=StagingCheckType.HEALTH,
            status=StagingCheckStatus.FAIL,
            duration_ms=120,
            summary="Health check failed",
        )

    async def teardown_staging(self, deployment_id: str) -> bool:
        if deployment_id in self.active_deployments:
            del self.active_deployments[deployment_id]
            return True
        return True
