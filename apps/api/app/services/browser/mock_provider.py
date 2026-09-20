import uuid
import time
from typing import List, Optional
from app.services.browser.base import BaseBrowserProvider
from app.services.browser.models import (
    BrowserScenario,
    BrowserRunResult,
    BrowserRunStatus,
    BrowserStepResult,
    BrowserFailureType,
    BrowserAction,
    ConsoleLogEvent,
    NetworkErrorEvent,
    SelectorStrategy
)
from app.services.browser.policies import BrowserSecurityPolicy, CredentialRedactor
from app.services.browser.classifier import BrowserFailureClassifier

class MockBrowserProvider(BaseBrowserProvider):
    """
    Deterministic Mock Browser Provider for testing DevOnCall browser verification offline.
    Handles Scenarios A-F without requiring Playwright binaries or real browser execution.
    """

    @property
    def provider_name(self) -> str:
        return "MOCK_BROWSER"

    async def run_scenario(
        self,
        scenario: BrowserScenario,
        project_id: str,
        workspace_id: str,
        agent_run_id: Optional[str] = None,
        allowed_base_urls: Optional[List[str]] = None
    ) -> BrowserRunResult:
        policy = BrowserSecurityPolicy(allowed_base_urls=allowed_base_urls)
        is_valid, reason = policy.validate_url(scenario.base_url)

        run_id = f"mock-brun-{uuid.uuid4().hex[:8]}"

        if not is_valid:
            return BrowserRunResult(
                id=run_id,
                project_id=project_id,
                agent_run_id=agent_run_id,
                workspace_id=workspace_id,
                scenario_id=scenario.id,
                provider_type=self.provider_name,
                status=BrowserRunStatus.BLOCKED,
                base_url=scenario.base_url,
                error_type=BrowserFailureType.BLOCKED_URL,
                error_message=reason
            )

        step_results: List[BrowserStepResult] = []
        console_errors: List[ConsoleLogEvent] = []
        network_errors: List[NetworkErrorEvent] = []
        screenshot_paths: List[str] = []

        overall_status = BrowserRunStatus.PASSED
        current_url = scenario.base_url
        passed_steps = 0
        failed_steps = 0

        start_time = time.time()

        for step in scenario.steps:
            strat = policy.determine_selector_strategy(step.selector)

            # Scenario A: Standard Success
            if scenario.id == "login-smoke" or scenario.id == "dashboard-navigation":
                if step.action == BrowserAction.NAVIGATE:
                    current_url = f"{scenario.base_url}{step.path or ''}"

                step_results.append(BrowserStepResult(
                    step_index=step.step_index,
                    action=step.action,
                    selector=step.selector,
                    selector_strategy=strat,
                    status=BrowserRunStatus.PASSED,
                    duration_ms=45,
                    observed_value=CredentialRedactor.redact(step.value) if step.value else None
                ))
                passed_steps += 1

            # Scenario B: Element Missing Test
            elif scenario.id == "element-missing-test":
                if step.action == BrowserAction.ASSERT_VISIBLE:
                    overall_status = BrowserRunStatus.FAILED
                    failed_steps += 1
                    step_results.append(BrowserStepResult(
                        step_index=step.step_index,
                        action=step.action,
                        selector=step.selector,
                        selector_strategy=strat,
                        status=BrowserRunStatus.FAILED,
                        duration_ms=120,
                        error=f"Element '{step.selector}' not found on page {current_url}",
                        screenshot_path=f"workspaces/{workspace_id}/artifacts/screenshot-step{step.step_index}.png"
                    ))
                    screenshot_paths.append(f"workspaces/{workspace_id}/artifacts/screenshot-step{step.step_index}.png")
                    break
                else:
                    step_results.append(BrowserStepResult(
                        step_index=step.step_index,
                        action=step.action,
                        selector=step.selector,
                        selector_strategy=strat,
                        status=BrowserRunStatus.PASSED,
                        duration_ms=30
                    ))
                    passed_steps += 1

            # Scenario C: Assertion Text Mismatch Test
            elif scenario.id == "assertion-failure-test":
                if step.action == BrowserAction.ASSERT_TEXT:
                    overall_status = BrowserRunStatus.FAILED
                    failed_steps += 1
                    step_results.append(BrowserStepResult(
                        step_index=step.step_index,
                        action=step.action,
                        selector=step.selector,
                        selector_strategy=strat,
                        status=BrowserRunStatus.FAILED,
                        duration_ms=80,
                        error=f"Expected text '{step.expected_text}' but found 'DevOnCall'",
                        screenshot_path=f"workspaces/{workspace_id}/artifacts/screenshot-step{step.step_index}.png"
                    ))
                    screenshot_paths.append(f"workspaces/{workspace_id}/artifacts/screenshot-step{step.step_index}.png")
                    break
                else:
                    step_results.append(BrowserStepResult(
                        step_index=step.step_index,
                        action=step.action,
                        selector=step.selector,
                        selector_strategy=strat,
                        status=BrowserRunStatus.PASSED,
                        duration_ms=30
                    ))
                    passed_steps += 1

            # Scenario D: Application Unavailable
            elif scenario.id == "app-unavailable-test":
                overall_status = BrowserRunStatus.FAILED
                failed_steps += 1
                step_results.append(BrowserStepResult(
                    step_index=step.step_index,
                    action=step.action,
                    selector=step.selector,
                    selector_strategy=strat,
                    status=BrowserRunStatus.FAILED,
                    duration_ms=250,
                    error=f"ERR_CONNECTION_REFUSED at {scenario.base_url}{step.path or ''}"
                ))
                break

            # Scenario E: Network Error Test
            elif scenario.id == "network-error-test":
                if step.action == BrowserAction.CLICK:
                    overall_status = BrowserRunStatus.FAILED
                    failed_steps += 1
                    net_err = NetworkErrorEvent(
                        url=f"{scenario.base_url}/api/v1/auth/login",
                        method="POST",
                        status_code=500,
                        resource_type="xhr",
                        failure_text="Internal Server Error: Database Connection Failed"
                    )
                    network_errors.append(net_err)
                    step_results.append(BrowserStepResult(
                        step_index=step.step_index,
                        action=step.action,
                        selector=step.selector,
                        selector_strategy=strat,
                        status=BrowserRunStatus.FAILED,
                        duration_ms=150,
                        error="HTTP 500 Internal Server Error during POST /api/v1/auth/login"
                    ))
                    break
                else:
                    step_results.append(BrowserStepResult(
                        step_index=step.step_index,
                        action=step.action,
                        selector=step.selector,
                        selector_strategy=strat,
                        status=BrowserRunStatus.PASSED,
                        duration_ms=30
                    ))
                    passed_steps += 1

            # Scenario F: Console Error Test
            elif scenario.id == "console-error-test":
                overall_status = BrowserRunStatus.FAILED
                failed_steps += 1
                c_err = ConsoleLogEvent(
                    level="ERROR",
                    text="Uncaught TypeError: Cannot read property 'user' of undefined at src/components/Header.tsx:42"
                )
                console_errors.append(c_err)
                step_results.append(BrowserStepResult(
                    step_index=step.step_index,
                    action=step.action,
                    selector=step.selector,
                    selector_strategy=strat,
                    status=BrowserRunStatus.FAILED,
                    duration_ms=90,
                    error="Uncaught TypeError in browser console."
                ))
                break
            else:
                step_results.append(BrowserStepResult(
                    step_index=step.step_index,
                    action=step.action,
                    selector=step.selector,
                    selector_strategy=strat,
                    status=BrowserRunStatus.PASSED,
                    duration_ms=30
                ))
                passed_steps += 1

        duration_ms = int((time.time() - start_time) * 1000)

        raw_result = BrowserRunResult(
            id=run_id,
            project_id=project_id,
            agent_run_id=agent_run_id,
            workspace_id=workspace_id,
            scenario_id=scenario.id,
            provider_type=self.provider_name,
            status=overall_status,
            base_url=scenario.base_url,
            current_url=current_url,
            duration_ms=duration_ms,
            step_count=len(scenario.steps),
            passed_steps=passed_steps,
            failed_steps=failed_steps,
            step_results=step_results,
            console_errors=console_errors,
            network_errors=network_errors,
            screenshot_paths=screenshot_paths
        )

        return BrowserFailureClassifier.classify(raw_result)
