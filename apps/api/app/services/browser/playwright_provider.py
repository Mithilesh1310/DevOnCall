import uuid
import time
import asyncio
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
    NetworkErrorEvent
)
from app.services.browser.policies import BrowserSecurityPolicy, CredentialRedactor
from app.services.browser.artifacts import BrowserArtifactManager
from app.services.browser.classifier import BrowserFailureClassifier

class PlaywrightBrowserProvider(BaseBrowserProvider):
    """
    Playwright Browser Provider executing automated UI verification via real Chromium/WebKit/Firefox browsers.
    Ensures context isolation, network & console monitoring, and clean process destruction.
    """

    @property
    def provider_name(self) -> str:
        return "PLAYWRIGHT_BROWSER"

    async def run_scenario(
        self,
        scenario: BrowserScenario,
        project_id: str,
        workspace_id: str,
        agent_run_id: Optional[str] = None,
        allowed_base_urls: Optional[List[str]] = None
    ) -> BrowserRunResult:
        run_id = f"pw-brun-{uuid.uuid4().hex[:8]}"
        policy = BrowserSecurityPolicy(allowed_base_urls=allowed_base_urls)
        is_valid, reason = policy.validate_url(scenario.base_url)

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

        # Check if playwright package is installed
        try:
            from playwright.async_api import async_playwright
        except ImportError:
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
                error_message="PLAYWRIGHT RUNTIME = BLOCKED (Playwright python package not installed)"
            )

        step_results: List[BrowserStepResult] = []
        console_errors: List[ConsoleLogEvent] = []
        network_errors: List[NetworkErrorEvent] = []
        screenshot_paths: List[str] = []
        artifact_mgr = BrowserArtifactManager()

        start_time = time.time()
        overall_status = BrowserRunStatus.PASSED
        passed_steps = 0
        failed_steps = 0
        current_url = scenario.base_url

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    ignore_https_errors=True,
                    user_agent="DevOnCall-BrowserAgent/1.0"
                )

                page = await context.new_page()

                # Set up Console listener
                def handle_console(msg):
                    if msg.type in ["error", "warning"]:
                        console_errors.append(ConsoleLogEvent(
                            level=msg.type.upper(),
                            text=CredentialRedactor.redact(msg.text),
                            location=msg.location.get("url") if msg.location else None
                        ))

                page.on("console", handle_console)

                # Set up Network Response failure listener
                def handle_response(response):
                    if response.status >= 400:
                        network_errors.append(NetworkErrorEvent(
                            url=CredentialRedactor.redact(response.url),
                            method=response.request.method,
                            status_code=response.status,
                            resource_type=response.request.resource_type,
                            failure_text=f"HTTP {response.status} {response.status_text}"
                        ))

                page.on("response", handle_response)

                # Execute Scenario Steps
                for step in scenario.steps:
                    strat = policy.determine_selector_strategy(step.selector)
                    step_start = time.time()

                    try:
                        if step.action == BrowserAction.NAVIGATE:
                            nav_url = f"{scenario.base_url}{step.path or ''}"
                            valid_nav, nav_reason = policy.validate_url(nav_url)
                            if not valid_nav:
                                raise ValueError(f"Navigation blocked: {nav_reason}")

                            await page.goto(nav_url, timeout=step.timeout_ms)
                            current_url = page.url

                        elif step.action == BrowserAction.CLICK:
                            if not step.selector:
                                raise ValueError("CLICK action requires selector")
                            await page.click(step.selector, timeout=step.timeout_ms)

                        elif step.action == BrowserAction.FILL:
                            if not step.selector:
                                raise ValueError("FILL action requires selector")
                            await page.fill(step.selector, step.value or "", timeout=step.timeout_ms)

                        elif step.action == BrowserAction.SELECT:
                            if not step.selector:
                                raise ValueError("SELECT action requires selector")
                            await page.select_option(step.selector, step.value or "", timeout=step.timeout_ms)

                        elif step.action == BrowserAction.ASSERT_VISIBLE:
                            if not step.selector:
                                raise ValueError("ASSERT_VISIBLE action requires selector")
                            await page.wait_for_selector(step.selector, state="visible", timeout=step.timeout_ms)

                        elif step.action == BrowserAction.ASSERT_TEXT:
                            if not step.selector:
                                raise ValueError("ASSERT_TEXT action requires selector")
                            elem = await page.wait_for_selector(step.selector, timeout=step.timeout_ms)
                            actual_text = (await elem.text_content()) if elem else ""
                            if (step.expected_text or "") not in (actual_text or ""):
                                raise AssertionError(f"Expected text '{step.expected_text}' but found '{actual_text}'")

                        elif step.action == BrowserAction.ASSERT_URL:
                            expected_path = step.path or ""
                            if expected_path not in page.url:
                                raise AssertionError(f"Expected URL to contain '{expected_path}' but got '{page.url}'")

                        elif step.action == BrowserAction.WAIT_FOR:
                            if step.selector:
                                await page.wait_for_selector(step.selector, timeout=step.timeout_ms)
                            else:
                                await asyncio.sleep(step.timeout_ms / 1000.0)

                        elif step.action == BrowserAction.SCREENSHOT:
                            shot_bytes = await page.screenshot(full_page=False)
                            shot_name = f"screenshot-step{step.step_index}.png"
                            saved_path = artifact_mgr.save_screenshot(workspace_id, shot_name, shot_bytes)
                            screenshot_paths.append(saved_path)

                        step_dur = int((time.time() - step_start) * 1000)
                        step_results.append(BrowserStepResult(
                            step_index=step.step_index,
                            action=step.action,
                            selector=step.selector,
                            selector_strategy=strat,
                            status=BrowserRunStatus.PASSED,
                            duration_ms=step_dur,
                            observed_value=CredentialRedactor.redact(step.value) if step.value else None
                        ))
                        passed_steps += 1

                    except Exception as step_err:
                        step_dur = int((time.time() - step_start) * 1000)
                        overall_status = BrowserRunStatus.FAILED
                        failed_steps += 1

                        # Take Failure Screenshot
                        shot_path = None
                        try:
                            shot_bytes = await page.screenshot(full_page=False)
                            shot_name = f"failure-step{step.step_index}.png"
                            shot_path = artifact_mgr.save_screenshot(workspace_id, shot_name, shot_bytes)
                            screenshot_paths.append(shot_path)
                        except Exception:
                            pass

                        step_results.append(BrowserStepResult(
                            step_index=step.step_index,
                            action=step.action,
                            selector=step.selector,
                            selector_strategy=strat,
                            status=BrowserRunStatus.FAILED,
                            duration_ms=step_dur,
                            error=CredentialRedactor.redact(str(step_err)),
                            screenshot_path=shot_path
                        ))
                        break

                await context.close()
                await browser.close()

        except Exception as launch_err:
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
                error_message=f"PLAYWRIGHT RUNTIME = BLOCKED ({str(launch_err)})"
            )

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
