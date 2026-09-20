import pytest
from app.services.browser import (
    MockBrowserProvider,
    BrowserManager,
    PREDEFINED_SCENARIOS,
    get_scenario,
    BrowserRunStatus,
    BrowserFailureType,
    SelectorStrategy,
    BrowserSecurityPolicy,
    BrowserFailureClassifier
)
from app.services.browser.models import BrowserRunResult
from app.services.agent.tools.browser_tool import BrowserValidationTool

@pytest.mark.asyncio
async def test_mock_browser_provider_scenario_a_pass():
    provider = MockBrowserProvider()
    scenario = get_scenario("login-smoke")
    assert scenario is not None

    result = await provider.run_scenario(
        scenario=scenario,
        project_id="test-proj",
        workspace_id="test-ws"
    )

    assert result.status == BrowserRunStatus.PASSED
    assert result.passed_steps == len(scenario.steps)
    assert result.failed_steps == 0
    assert result.error_type is None

@pytest.mark.asyncio
async def test_mock_browser_provider_scenario_b_element_missing():
    provider = MockBrowserProvider()
    scenario = get_scenario("element-missing-test")
    assert scenario is not None

    result = await provider.run_scenario(
        scenario=scenario,
        project_id="test-proj",
        workspace_id="test-ws"
    )

    assert result.status == BrowserRunStatus.FAILED
    assert result.error_type == BrowserFailureType.ELEMENT_NOT_FOUND
    assert result.failed_steps == 1

@pytest.mark.asyncio
async def test_mock_browser_provider_scenario_c_assertion_failure():
    provider = MockBrowserProvider()
    scenario = get_scenario("assertion-failure-test")
    assert scenario is not None

    result = await provider.run_scenario(
        scenario=scenario,
        project_id="test-proj",
        workspace_id="test-ws"
    )

    assert result.status == BrowserRunStatus.FAILED
    assert result.error_type == BrowserFailureType.ASSERTION_FAILED

@pytest.mark.asyncio
async def test_mock_browser_provider_scenario_d_app_unavailable():
    provider = MockBrowserProvider()
    scenario = get_scenario("app-unavailable-test")
    assert scenario is not None

    result = await provider.run_scenario(
        scenario=scenario,
        project_id="test-proj",
        workspace_id="test-ws"
    )

    assert result.status == BrowserRunStatus.FAILED

@pytest.mark.asyncio
async def test_mock_browser_provider_scenario_e_network_error():
    provider = MockBrowserProvider()
    scenario = get_scenario("network-error-test")
    assert scenario is not None

    result = await provider.run_scenario(
        scenario=scenario,
        project_id="test-proj",
        workspace_id="test-ws"
    )

    assert result.status == BrowserRunStatus.FAILED
    assert result.error_type == BrowserFailureType.NETWORK_ERROR
    assert len(result.network_errors) > 0

@pytest.mark.asyncio
async def test_mock_browser_provider_scenario_f_console_error():
    provider = MockBrowserProvider()
    scenario = get_scenario("console-error-test")
    assert scenario is not None

    result = await provider.run_scenario(
        scenario=scenario,
        project_id="test-proj",
        workspace_id="test-ws"
    )

    assert result.status == BrowserRunStatus.FAILED
    assert result.error_type == BrowserFailureType.CONSOLE_ERROR
    assert len(result.console_errors) > 0

def test_selector_strategy_detection():
    policy = BrowserSecurityPolicy()

    assert policy.determine_selector_strategy("[data-testid='btn']") == SelectorStrategy.DATA_TESTID
    assert policy.determine_selector_strategy("[role='button']") == SelectorStrategy.ACCESSIBLE_ROLE
    assert policy.determine_selector_strategy("button[name='submit']") == SelectorStrategy.LABEL
    assert policy.determine_selector_strategy("div.container > p:nth-child(2)") == SelectorStrategy.FRAGILE_CSS

def test_repository_file_correlation():
    raw_res = BrowserRunResult(
        id="br-1",
        project_id="p1",
        workspace_id="ws1",
        scenario_id="login-smoke",
        provider_type="MOCK",
        status=BrowserRunStatus.FAILED,
        base_url="http://localhost:3000",
        network_errors=[{
            "url": "http://localhost:3000/api/v1/auth/login",
            "method": "POST",
            "status_code": 500
        }]
    )

    repo_tree = [
        {"path": "apps/api/app/api/auth.py", "type": "file"},
        {"path": "apps/api/app/api/login.py", "type": "file"},
        {"path": "apps/web/src/pages/index.tsx", "type": "file"}
    ]

    classified = BrowserFailureClassifier.classify(raw_res, repo_tree)
    assert classified.suspected_file is not None
    assert "login" in classified.suspected_file

@pytest.mark.asyncio
async def test_browser_validation_tool_execution():
    tool = BrowserValidationTool()
    class DummyContext:
        workspace_path = "ws-test-123"

    res = await tool.execute({
        "project_id": "proj-1",
        "scenario_id": "login-smoke",
        "base_url": "http://localhost:3000",
        "use_mock": True
    }, DummyContext())

    assert res.success is True
    assert res.data["status"] == "PASSED"
    assert res.data["scenario_id"] == "login-smoke"
    assert res.data["passed_steps"] > 0

