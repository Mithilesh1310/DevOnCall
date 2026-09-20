import logging
from typing import List, Dict, Any, Optional
from app.services.agent.validation.models import ValidationResult, AgentDecision, FailureType

logger = logging.getLogger("devoncall.validation.repair_policy")

MAX_AGENT_ITERATIONS = 10
MAX_VALIDATION_RUNS = 10
MAX_REPAIR_ATTEMPTS = 5
MAX_SAME_FAILURE_RETRIES = 2
MAX_BROWSER_RUNS = 5

class RepairPolicy:
    """
    Decides agent action after validation execution while enforcing strict bounded iteration limits
    and repeated failure detection rules.
    """

    @classmethod
    def evaluate(
        cls,
        current_result: ValidationResult,
        validation_history: List[Dict[str, Any]],
        iteration_count: int,
        repair_attempt_count: int,
        browser_run_count: int = 0
    ) -> AgentDecision:
        # 1. Enforce Max Bounded Limits
        if iteration_count >= MAX_AGENT_ITERATIONS:
            logger.warning(f"Limit reached: MAX_AGENT_ITERATIONS ({MAX_AGENT_ITERATIONS})")
            return AgentDecision(
                action="STOP",
                reason=f"Reached maximum agent iteration limit ({MAX_AGENT_ITERATIONS}).",
                confidence=1.0,
                evidence=[f"iteration_count = {iteration_count}"]
            )

        if len(validation_history) >= MAX_VALIDATION_RUNS:
            logger.warning(f"Limit reached: MAX_VALIDATION_RUNS ({MAX_VALIDATION_RUNS})")
            return AgentDecision(
                action="STOP",
                reason=f"Reached maximum validation run limit ({MAX_VALIDATION_RUNS}).",
                confidence=1.0,
                evidence=[f"validation_runs = {len(validation_history)}"]
            )

        if browser_run_count >= MAX_BROWSER_RUNS:
            logger.warning(f"Limit reached: MAX_BROWSER_RUNS ({MAX_BROWSER_RUNS})")
            return AgentDecision(
                action="HUMAN_REVIEW",
                reason=f"Reached maximum browser validation run limit ({MAX_BROWSER_RUNS}). Flagging for human review.",
                confidence=1.0,
                evidence=[f"browser_run_count = {browser_run_count}"]
            )

        if repair_attempt_count >= MAX_REPAIR_ATTEMPTS:
            logger.warning(f"Limit reached: MAX_REPAIR_ATTEMPTS ({MAX_REPAIR_ATTEMPTS})")
            return AgentDecision(
                action="HUMAN_REVIEW",
                reason=f"Reached maximum repair attempt limit ({MAX_REPAIR_ATTEMPTS}). Flagging for human review.",
                confidence=1.0,
                evidence=[f"repair_attempts = {repair_attempt_count}"]
            )


        # 2. Evaluate PASSED Validation Result
        if current_result.status == "PASSED":
            return AgentDecision(
                action="CONTINUE",
                reason="Validation passed cleanly.",
                confidence=1.0,
                evidence=["status = PASSED", f"exit_code = {current_result.exit_code}"]
            )

        # 3. Handle Sandbox BLOCKED / TIMEOUT / RESOURCE_LIMIT
        if current_result.status == "BLOCKED":
            return AgentDecision(
                action="STOP",
                reason="Sandbox environment is BLOCKED or unavailable.",
                confidence=1.0,
                evidence=[current_result.stderr or "DOCKER_UNAVAILABLE"]
            )

        if current_result.failure_type == FailureType.TIMEOUT:
            return AgentDecision(
                action="STOP",
                reason="Validation run timed out repeatedly.",
                confidence=0.9,
                evidence=["status = TIMED_OUT"]
            )

        # 4. Check for Repeated Same Failure (Error Message + Line matching > MAX_SAME_FAILURE_RETRIES)
        same_failure_count = cls.count_same_failures(current_result, validation_history)
        if same_failure_count >= MAX_SAME_FAILURE_RETRIES:
            logger.warning(f"Repeated failure detected: same error occurred {same_failure_count} times")
            return AgentDecision(
                action="HUMAN_REVIEW",
                reason=f"Same validation failure repeated {same_failure_count} times without resolution. Flagging for human review.",
                confidence=1.0,
                evidence=[f"same_failure_count = {same_failure_count}", f"error = {current_result.summary}"]
            )

        # 5. Handle Known Code Failures (TEST, TYPECHECK, LINT, BUILD)
        if current_result.failure_type in [
            FailureType.TEST_FAILURE, FailureType.TYPE_ERROR, FailureType.LINT_FAILURE, FailureType.BUILD_FAILURE
        ]:
            return AgentDecision(
                action="FIX",
                reason=f"Identified {current_result.failure_type.value} in {current_result.affected_files[0] if current_result.affected_files else 'workspace'}.",
                confidence=0.9,
                evidence=[d.message for d in current_result.diagnostics[:2]] if current_result.diagnostics else [current_result.summary],
                target_files=current_result.affected_files
            )

        # 6. Handle Dependency or Configuration Errors
        if current_result.failure_type in [FailureType.DEPENDENCY_ERROR, FailureType.CONFIGURATION_ERROR]:
            return AgentDecision(
                action="HUMAN_REVIEW",
                reason=f"Environment or dependency issue ({current_result.failure_type.value}) requires human intervention.",
                confidence=0.85,
                evidence=[current_result.stderr[:200] if current_result.stderr else current_result.summary]
            )

        # 7. Default Unknown / Low Confidence Failure
        return AgentDecision(
            action="HUMAN_REVIEW",
            reason="Unrecognized validation failure or low confidence diagnostic. Requiring human review.",
            confidence=0.5,
            evidence=[current_result.summary]
        )

    @classmethod
    def count_same_failures(cls, current_result: ValidationResult, history: List[Dict[str, Any]]) -> int:
        if not history or not current_result.diagnostics:
            return 1

        cur_msg = current_result.diagnostics[0].message if current_result.diagnostics else ""
        cur_file = current_result.diagnostics[0].file if current_result.diagnostics else ""

        match_count = 1
        for item in reversed(history):
            past_diags = item.get("diagnostics", [])
            if past_diags:
                p_msg = past_diags[0].get("message", "")
                p_file = past_diags[0].get("file", "")
                if p_msg == cur_msg and (not cur_file or p_file == cur_file):
                    match_count += 1
                else:
                    break
        return match_count
