import pytest
from app.services.agent.validation.failure_classifier import FailureClassifier
from app.services.agent.validation.analyzer import ValidationAnalyzer
from app.services.agent.validation.models import FailureType

def test_failure_classifier():
    # TS Error
    assert FailureClassifier.classify("TYPECHECK", "FAILED", 1, "src/main.ts(10,5): error TS2322: Type 'number' is not assignable to type 'string'.", "") == FailureType.TYPE_ERROR

    # Pytest Failure
    assert FailureClassifier.classify("TEST", "FAILED", 1, "FAIL test_user.py - AssertionError: 404 != 200", "") == FailureType.TEST_FAILURE

    # ESLint Failure
    assert FailureClassifier.classify("LINT", "FAILED", 1, "src/app.ts: line 15, col 2: Unexpected var, use let or const instead", "") == FailureType.LINT_FAILURE

    # Timeout
    assert FailureClassifier.classify("TEST", "TIMED_OUT", -1, "", "Task timed out after 120s") == FailureType.TIMEOUT

    # Dependency Error
    assert FailureClassifier.classify("BUILD", "FAILED", 1, "", "ModuleNotFoundError: No module named 'fastapi'") == FailureType.DEPENDENCY_ERROR

def test_validation_analyzer_extraction_and_correlation():
    stdout = "src/services/user.ts(42,17): error TS2532: Object is possibly 'undefined'."
    stderr = ""
    snapshot = {
        "tree": [
            {"path": "src/services/user.ts", "type": "file"},
            {"path": "src/index.ts", "type": "file"}
        ]
    }

    res = ValidationAnalyzer.analyze(
        sandbox_run_id="sb-100",
        status="FAILED",
        command_type="TYPECHECK",
        exit_code=1,
        stdout=stdout,
        stderr=stderr,
        repository_snapshot=snapshot
    )

    assert res.status == "FAILED"
    assert res.failure_type == FailureType.TYPE_ERROR
    assert len(res.diagnostics) == 1
    assert res.diagnostics[0].file == "src/services/user.ts"
    assert res.diagnostics[0].line == 42
    assert res.diagnostics[0].column == 17
    assert res.diagnostics[0].code == "TS2532"
    assert "src/services/user.ts" in res.affected_files

def test_validation_analyzer_passed():
    res = ValidationAnalyzer.analyze(
        sandbox_run_id="sb-101",
        status="PASSED",
        command_type="TEST",
        exit_code=0,
        stdout="5 passed in 0.05s",
        stderr=""
    )
    assert res.status == "PASSED"
    assert res.failure_type is None
    assert res.suggested_action == "CONTINUE"
