import pytest
from app.services.agent.validation.repair_policy import RepairPolicy
from app.services.agent.validation.models import ValidationResult, FailureType, FailureDiagnostic

def test_repair_policy_continue_on_pass():
    result = ValidationResult(
        sandbox_run_id="sb-1",
        status="PASSED",
        command_type="TEST",
        exit_code=0,
        summary="Passed",
        stdout="",
        stderr="",
        failure_type=None,
        diagnostics=[],
        affected_files=[],
        suggested_action="CONTINUE"
    )
    decision = RepairPolicy.evaluate(result, [], iteration_count=1, repair_attempt_count=0)
    assert decision.action == "CONTINUE"

def test_repair_policy_fix_on_code_failure():
    result = ValidationResult(
        sandbox_run_id="sb-2",
        status="FAILED",
        command_type="TYPECHECK",
        exit_code=1,
        summary="Type error in user.ts",
        stdout="",
        stderr="",
        failure_type=FailureType.TYPE_ERROR,
        diagnostics=[FailureDiagnostic(message="TS2532", file="user.ts", line=10, column=5, source="compiler")],
        affected_files=["user.ts"],
        suggested_action="FIX"
    )
    decision = RepairPolicy.evaluate(result, [], iteration_count=1, repair_attempt_count=0)
    assert decision.action == "FIX"
    assert "user.ts" in decision.target_files

def test_repair_policy_repeated_failure_human_review():
    result = ValidationResult(
        sandbox_run_id="sb-3",
        status="FAILED",
        command_type="TEST",
        exit_code=1,
        summary="AssertionError",
        stdout="",
        stderr="",
        failure_type=FailureType.TEST_FAILURE,
        diagnostics=[FailureDiagnostic(message="AssertionError: 404 != 200", file="test_app.py", line=15, source="pytest")],
        affected_files=["test_app.py"],
        suggested_action="FIX"
    )
    history = [
        {"diagnostics": [{"message": "AssertionError: 404 != 200", "file": "test_app.py"}]},
        {"diagnostics": [{"message": "AssertionError: 404 != 200", "file": "test_app.py"}]}
    ]

    decision = RepairPolicy.evaluate(result, history, iteration_count=3, repair_attempt_count=2)
    assert decision.action == "HUMAN_REVIEW"
    assert "Same validation failure repeated" in decision.reason

def test_repair_policy_limits_enforcement():
    result = ValidationResult(
        sandbox_run_id="sb-4",
        status="FAILED",
        command_type="TEST",
        exit_code=1,
        summary="Fail",
        stdout="",
        stderr="",
        failure_type=FailureType.TEST_FAILURE,
        diagnostics=[],
        affected_files=[],
        suggested_action="FIX"
    )
    # Iteration limit reached
    dec_iter = RepairPolicy.evaluate(result, [], iteration_count=10, repair_attempt_count=1)
    assert dec_iter.action == "STOP"
    assert "maximum agent iteration limit" in dec_iter.reason

    # Repair attempt limit reached
    dec_repair = RepairPolicy.evaluate(result, [], iteration_count=5, repair_attempt_count=5)
    assert dec_repair.action == "HUMAN_REVIEW"
    assert "maximum repair attempt limit" in dec_repair.reason
