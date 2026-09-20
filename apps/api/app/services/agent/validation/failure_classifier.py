import re
import logging
from typing import Optional, Tuple
from app.services.agent.validation.models import FailureType

logger = logging.getLogger("devoncall.validation.classifier")

class FailureClassifier:
    """
    Deterministic failure classifier for validation runs.
    Analyzes command type, exit code, stdout, and stderr output patterns.
    """

    @classmethod
    def classify(cls, command_type: str, status: str, exit_code: int, stdout: str, stderr: str) -> FailureType:
        if status == "TIMED_OUT":
            return FailureType.TIMEOUT

        if status == "BLOCKED" or "RESOURCE_LIMIT" in stderr.upper():
            return FailureType.RESOURCE_LIMIT

        combined_text = f"{stdout}\n{stderr}"
        text_lower = combined_text.lower()

        # 1. Check TypeScript compilation error patterns (TS1234, tsc errors)
        if "ts" in command_type.lower() or "typecheck" in command_type.lower() or "error ts" in text_lower or re.search(r"\bTS\d{4}\b", combined_text):
            return FailureType.TYPE_ERROR

        # 2. Check ESLint / Linter error patterns
        if "lint" in command_type.lower() or "eslint" in text_lower or "flake8" in text_lower or "linter" in text_lower:
            return FailureType.LINT_FAILURE

        # 3. Check Dependency / Module import errors
        if "modulenotfounderror" in text_lower or "cannot find module" in text_lower or "pip install" in text_lower or "npm err!" in text_lower:
            return FailureType.DEPENDENCY_ERROR

        # 4. Check Test framework failures (Pytest / Jest)
        if "test" in command_type.lower() or "assertionerror" in text_lower or "failed:" in text_lower or "FAIL" in stdout or "pytest" in text_lower:
            return FailureType.TEST_FAILURE

        # 5. Check Build framework failures
        if "build" in command_type.lower() or "build failed" in text_lower or "compilation error" in text_lower:
            return FailureType.BUILD_FAILURE

        # 6. Check Configuration / Missing file errors
        if "file not found" in text_lower or "config" in text_lower:
            return FailureType.CONFIGURATION_ERROR

        if exit_code != 0:
            if command_type == "TEST":
                return FailureType.TEST_FAILURE
            elif command_type == "BUILD":
                return FailureType.BUILD_FAILURE
            elif command_type == "LINT":
                return FailureType.LINT_FAILURE
            elif command_type == "TYPECHECK":
                return FailureType.TYPE_ERROR

        return FailureType.UNKNOWN
