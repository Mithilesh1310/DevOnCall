import logging
from typing import List, Dict, Any, Optional
from app.services.sandbox.base import CommandType

logger = logging.getLogger("devoncall.validation.planner")

class ValidationPlanner:
    """
    Intelligently determines ordered validation command sequences based on modified file extensions
    and previous failure diagnostics.
    """

    @classmethod
    def plan_validations(
        cls,
        files_changed: List[str],
        runtime: str = "python",
        previous_failure_type: Optional[str] = None
    ) -> List[CommandType]:
        # If previous validation failed, re-run that target validation first
        if previous_failure_type:
            if previous_failure_type == "TYPE_ERROR":
                return [CommandType.TYPECHECK, CommandType.TEST]
            elif previous_failure_type == "LINT_FAILURE":
                return [CommandType.LINT, CommandType.TEST]
            elif previous_failure_type == "BUILD_FAILURE":
                return [CommandType.BUILD, CommandType.TEST]

        has_ts = any(f.endswith(".ts") or f.endswith(".tsx") for f in files_changed)
        has_py = any(f.endswith(".py") for f in files_changed)

        if has_ts:
            return [CommandType.TYPECHECK, CommandType.TEST]
        
        if has_py:
            return [CommandType.TEST, CommandType.LINT]

        return [CommandType.TEST]
