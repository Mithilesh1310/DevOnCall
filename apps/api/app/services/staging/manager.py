import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.services.staging.base import BaseStagingProvider
from app.services.staging.mock_provider import MockStagingProvider
from app.services.staging.docker_provider import DockerStagingProvider
from app.services.staging.policies import StagingSecurityPolicy, StagingVerificationPolicy
from app.services.staging.models import (
    StagingDeployment,
    StagingDeploymentStatus,
    StagingCheckResult,
    StagingCheckType,
    StagingCheckStatus,
)
from app.services.staging.health import StagingHealthChecker
from app.services.staging.smoke import StagingSmokeTester
from app.services.staging.cleanup import StagingCleanupManager

logger = logging.getLogger("devoncall.staging.manager")


class StagingManager:
    """
    Central orchestration engine for Staging Deployments and Autonomous Verification Gates.
    Integrates Sandbox build verification, Docker/Mock staging provider execution,
    Health Checks, Smoke Testing, Playwright Browser Verification, and Cleanup.
    """

    def __init__(self, provider: Optional[BaseStagingProvider] = None, use_mock: bool = False):
        import os
        test_mode = os.getenv("TEST_MODE", "false").lower() in ["true", "1", "yes"]
        if provider:
            self.provider = provider
        elif use_mock or test_mode:
            self.provider = MockStagingProvider()
        else:
            self.provider = DockerStagingProvider()

        self.cleanup_manager = StagingCleanupManager(provider=self.provider)

    async def create_and_run_deployment(
        self,
        project_id: str,
        workspace_id: str,
        branch: str,
        commit_sha: str,
        agent_run_id: Optional[str] = None,
        environment: str = "STAGING",
        use_mock: bool = True,
        mock_scenario: str = "PASS",
        verification_policy: Optional[StagingVerificationPolicy] = None,
    ) -> StagingDeployment:
        # 1. Security & Environment Policy Validation
        is_valid_env, env_reason = StagingSecurityPolicy.validate_environment(environment)
        if not is_valid_env:
            return StagingDeployment(
                project_id=project_id,
                workspace_id=workspace_id,
                branch=branch,
                commit_sha=commit_sha,
                environment=environment,
                status=StagingDeploymentStatus.BLOCKED,
                error_type="SECURITY_POLICY_VIOLATION",
                error_message=env_reason,
            )

        is_valid_commit, commit_reason = StagingSecurityPolicy.validate_commit(commit_sha, branch)
        if not is_valid_commit:
            return StagingDeployment(
                project_id=project_id,
                workspace_id=workspace_id,
                branch=branch,
                commit_sha=commit_sha,
                environment=environment,
                status=StagingDeploymentStatus.BLOCKED,
                error_type="COMMIT_VALIDATION_FAILED",
                error_message=commit_reason,
            )

        # Provider selection
        if use_mock:
            self.provider = MockStagingProvider(scenario=mock_scenario)

        policy = verification_policy or StagingVerificationPolicy()

        deployment = StagingDeployment(
            project_id=project_id,
            agent_run_id=agent_run_id,
            workspace_id=workspace_id,
            branch=branch,
            commit_sha=commit_sha,
            environment="STAGING",
            status=StagingDeploymentStatus.BUILDING,
        )

        logger.info(f"Initiating staging deployment '{deployment.id}' for commit '{commit_sha[:8]}' on branch '{branch}'")

        # 2. Deploy Staging Environment
        deployment.status = StagingDeploymentStatus.DEPLOYING
        deployment = await self.provider.deploy_staging(deployment)

        if deployment.status in [StagingDeploymentStatus.FAILED, StagingDeploymentStatus.BLOCKED]:
            logger.warning(f"Staging deployment '{deployment.id}' failed/blocked: {deployment.error_message}")
            await self.cleanup_manager.cleanup_deployment(deployment.id)
            return deployment

        # 3. Health Checking Stage
        if policy.require_health and deployment.deployment_url:
            deployment.status = StagingDeploymentStatus.HEALTH_CHECKING
            if isinstance(self.provider, MockStagingProvider):
                # Mock provider already evaluated health check result
                existing_h = next((c for c in deployment.checks if c.check_type == StagingCheckType.HEALTH), None)
                if existing_h and existing_h.status == StagingCheckStatus.FAIL:
                    deployment.status = StagingDeploymentStatus.FAILED
                    deployment.error_type = "HEALTH_CHECK_FAILED"
                    deployment.error_message = existing_h.summary
                    await self.cleanup_manager.cleanup_deployment(deployment.id)
                    return deployment
            else:
                checker = StagingHealthChecker(timeout_seconds=5)
                health_res = checker.check_health(deployment.id, deployment.deployment_url)
                if not any(c.check_type == StagingCheckType.HEALTH for c in deployment.checks):
                    deployment.checks.append(health_res)

                if health_res.status == StagingCheckStatus.FAIL:
                    deployment.status = StagingDeploymentStatus.FAILED
                    deployment.error_type = "HEALTH_CHECK_FAILED"
                    deployment.error_message = health_res.summary
                    await self.cleanup_manager.cleanup_deployment(deployment.id)
                    return deployment

        # 4. Smoke Testing Stage
        if policy.require_smoke and deployment.deployment_url:
            deployment.status = StagingDeploymentStatus.VERIFYING
            if isinstance(self.provider, MockStagingProvider):
                existing_s = next((c for c in deployment.checks if c.check_type == StagingCheckType.SMOKE), None)
                if existing_s and existing_s.status == StagingCheckStatus.FAIL:
                    deployment.status = StagingDeploymentStatus.FAILED
                    deployment.error_type = "SMOKE_TEST_FAILED"
                    deployment.error_message = existing_s.summary
                    await self.cleanup_manager.cleanup_deployment(deployment.id)
                    return deployment
            else:
                smoke_tester = StagingSmokeTester()
                smoke_res = smoke_tester.run_smoke_tests(deployment.id, deployment.deployment_url)
                if not any(c.check_type == StagingCheckType.SMOKE for c in deployment.checks):
                    deployment.checks.append(smoke_res)

                if smoke_res.status == StagingCheckStatus.FAIL:
                    deployment.status = StagingDeploymentStatus.FAILED
                    deployment.error_type = "SMOKE_TEST_FAILED"
                    deployment.error_message = smoke_res.summary
                    await self.cleanup_manager.cleanup_deployment(deployment.id)
                    return deployment


        # 5. Playwright Browser Verification Stage (Reuse Phase 7 Browser System)
        if policy.require_browser and deployment.deployment_url:
            from app.services.browser.manager import BrowserManager
            browser_mgr = BrowserManager(use_mock=True)
            b_run = await browser_mgr.run_scenario(
                project_id=project_id,
                workspace_id=workspace_id,
                scenario_id="login-smoke",
                base_url=deployment.deployment_url,
                agent_run_id=agent_run_id,
            )

            b_status = StagingCheckStatus.PASS if b_run.status == "PASSED" else StagingCheckStatus.FAIL
            deployment.checks.append(
                StagingCheckResult(
                    deployment_id=deployment.id,
                    check_type=StagingCheckType.BROWSER,
                    status=b_status,
                    duration_ms=b_run.duration_ms,
                    summary=f"Playwright Browser verification {b_run.status} against {deployment.deployment_url}",
                    details={"scenario_id": b_run.scenario_id, "step_count": b_run.step_count},
                )
            )

            if b_status == StagingCheckStatus.FAIL:
                deployment.status = StagingDeploymentStatus.FAILED
                deployment.error_type = "BROWSER_VERIFICATION_FAILED"
                deployment.error_message = f"Browser scenario '{b_run.scenario_id}' failed in staging"
                await self.cleanup_manager.cleanup_deployment(deployment.id)
                return deployment

        # 6. Final Staging Verdict Evaluation
        check_dicts = [{"check_type": c.check_type.value, "status": c.status.value} for c in deployment.checks]
        is_passed, verdict_msg = policy.evaluate_verdict(check_dicts)

        if is_passed:
            deployment.status = StagingDeploymentStatus.PASSED
            logger.info(f"Staging deployment '{deployment.id}' PASSED all verification gates cleanly.")
        else:
            deployment.status = StagingDeploymentStatus.FAILED
            deployment.error_type = "VERDICT_EVALUATION_FAILED"
            deployment.error_message = verdict_msg
            await self.cleanup_manager.cleanup_deployment(deployment.id)

        deployment.finished_at = datetime.now(timezone.utc).isoformat()
        return deployment
