from typing import Dict, Optional
from app.services.browser.models import BrowserScenario, BrowserStep, BrowserAction

PREDEFINED_SCENARIOS: Dict[str, BrowserScenario] = {
    "login-smoke": BrowserScenario(
        id="login-smoke",
        name="Login Smoke Test",
        description="Verifies navigating to /login, filling credentials, submitting, and asserting dashboard visibility.",
        base_url="http://localhost:3000",
        steps=[
            BrowserStep(step_index=1, action=BrowserAction.NAVIGATE, path="/login"),
            BrowserStep(step_index=2, action=BrowserAction.ASSERT_VISIBLE, selector="[data-testid='login-form']"),
            BrowserStep(step_index=3, action=BrowserAction.FILL, selector="[data-testid='email']", value="test@example.com"),
            BrowserStep(step_index=4, action=BrowserAction.FILL, selector="[data-testid='password']", value="secret123"),
            BrowserStep(step_index=5, action=BrowserAction.CLICK, selector="[data-testid='submit']"),
            BrowserStep(step_index=6, action=BrowserAction.ASSERT_URL, path="/dashboard"),
            BrowserStep(step_index=7, action=BrowserAction.ASSERT_VISIBLE, selector="[data-testid='dashboard']")
        ]
    ),
    "dashboard-navigation": BrowserScenario(
        id="dashboard-navigation",
        name="Dashboard Navigation Test",
        description="Verifies main page loads and header element is visible.",
        base_url="http://localhost:3000",
        steps=[
            BrowserStep(step_index=1, action=BrowserAction.NAVIGATE, path="/"),
            BrowserStep(step_index=2, action=BrowserAction.ASSERT_VISIBLE, selector="[data-testid='header']"),
            BrowserStep(step_index=3, action=BrowserAction.ASSERT_TEXT, selector="h1", expected_text="DevOnCall")
        ]
    ),
    "element-missing-test": BrowserScenario(
        id="element-missing-test",
        name="Element Missing Test Scenario",
        description="Attempts to interact with a non-existent element.",
        base_url="http://localhost:3000",
        steps=[
            BrowserStep(step_index=1, action=BrowserAction.NAVIGATE, path="/"),
            BrowserStep(step_index=2, action=BrowserAction.ASSERT_VISIBLE, selector="[data-testid='missing-element']")
        ]
    ),
    "assertion-failure-test": BrowserScenario(
        id="assertion-failure-test",
        name="Assertion Failure Test Scenario",
        description="Asserts text mismatch on header element.",
        base_url="http://localhost:3000",
        steps=[
            BrowserStep(step_index=1, action=BrowserAction.NAVIGATE, path="/"),
            BrowserStep(step_index=2, action=BrowserAction.ASSERT_TEXT, selector="h1", expected_text="Incorrect Title Text")
        ]
    ),
    "app-unavailable-test": BrowserScenario(
        id="app-unavailable-test",
        name="Application Unavailable Test Scenario",
        description="Simulates application start failure.",
        base_url="http://localhost:3000",
        steps=[
            BrowserStep(step_index=1, action=BrowserAction.NAVIGATE, path="/unreachable")
        ]
    ),
    "network-error-test": BrowserScenario(
        id="network-error-test",
        name="Network Error Test Scenario",
        description="Simulates API 500 error during submit.",
        base_url="http://localhost:3000",
        steps=[
            BrowserStep(step_index=1, action=BrowserAction.NAVIGATE, path="/login"),
            BrowserStep(step_index=2, action=BrowserAction.CLICK, selector="[data-testid='trigger-500']")
        ]
    ),
    "console-error-test": BrowserScenario(
        id="console-error-test",
        name="Console Error Test Scenario",
        description="Simulates unhandled JS exception on page.",
        base_url="http://localhost:3000",
        steps=[
            BrowserStep(step_index=1, action=BrowserAction.NAVIGATE, path="/broken-page")
        ]
    )
}

def get_scenario(scenario_id: str) -> Optional[BrowserScenario]:
    return PREDEFINED_SCENARIOS.get(scenario_id)
