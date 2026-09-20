import pytest
from app.services.staging.mock_provider import MockStagingProvider
from app.services.staging.docker_provider import DockerStagingProvider
from app.services.staging.manager import StagingManager
from app.services.staging.models import StagingDeployment, StagingDeploymentStatus, StagingCheckType, StagingCheckStatus
from app.services.staging.health import StagingHealthChecker
from app.services.staging.smoke import StagingSmokeTester
from app.services.staging.cleanup import StagingCleanupManager


@pytest.mark.asyncio
async def test_mock_staging_provider_scenarios():
    # PASS scenario
    pass_provider = MockStagingProvider(scenario="PASS")
    dep_pass = StagingDeployment(
        project_id="proj-1",
        workspace_id="ws-1",
        branch="devoncall/agent/fix-142",
        commit_sha="a1b2c3d4e5f6"
    )
    res_pass = await pass_provider.deploy_staging(dep_pass)
    assert res_pass.status == StagingDeploymentStatus.PASSED
    assert res_pass.deployment_url is not None
    assert len(res_pass.checks) == 5

    # BUILD_FAIL scenario
    build_fail_provider = MockStagingProvider(scenario="BUILD_FAIL")
    dep_b_fail = StagingDeployment(
        project_id="proj-1",
        workspace_id="ws-1",
        branch="devoncall/agent/fix-142",
        commit_sha="a1b2c3d4e5f6"
    )
    res_b_fail = await build_fail_provider.deploy_staging(dep_b_fail)
    assert res_b_fail.status == StagingDeploymentStatus.FAILED
    assert res_b_fail.error_type == "BUILD_ERROR"

    # HEALTH_FAIL scenario
    health_fail_provider = MockStagingProvider(scenario="HEALTH_FAIL")
    dep_h_fail = StagingDeployment(
        project_id="proj-1",
        workspace_id="ws-1",
        branch="devoncall/agent/fix-142",
        commit_sha="a1b2c3d4e5f6"
    )
    res_h_fail = await health_fail_provider.deploy_staging(dep_h_fail)
    assert res_h_fail.status == StagingDeploymentStatus.FAILED
    assert res_h_fail.error_type == "HEALTH_CHECK_FAILED"


@pytest.mark.asyncio
async def test_staging_manager_full_flow():
    manager = StagingManager(use_mock=True)

    run_res = await manager.create_and_run_deployment(
        project_id="proj-demo",
        workspace_id="ws-demo",
        branch="devoncall/agent/fix-99",
        commit_sha="998877665544",
        environment="STAGING",
        use_mock=True,
        mock_scenario="PASS"
    )

    assert run_res.status == StagingDeploymentStatus.PASSED
    assert run_res.deployment_url is not None
    assert run_res.environment == "STAGING"


def test_smoke_tester_allowlisted_endpoints():
    tester = StagingSmokeTester()

    # Empty URL fails gracefully
    res_fail = tester.run_smoke_tests("dep-1", "")
    assert res_fail.status == StagingCheckStatus.FAIL


@pytest.mark.asyncio
async def test_staging_cleanup_manager():
    provider = MockStagingProvider()
    cleanup_mgr = StagingCleanupManager(provider=provider)

    res = await cleanup_mgr.cleanup_deployment("dep-demo-123")
    assert res is True
