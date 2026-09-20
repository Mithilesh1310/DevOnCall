import re
from typing import Optional, List
from app.services.browser.models import (
    BrowserRunResult,
    BrowserFailureType,
    BrowserRunStatus,
    ConsoleLogEvent,
    NetworkErrorEvent
)

class BrowserFailureClassifier:
    """
    Deterministic failure classifier for browser test runs.
    Correlates evidence from step errors, network errors, and console logs
    to classify failure types and map suspected repository files.
    """

    @staticmethod
    def classify(run_result: BrowserRunResult, repository_tree: Optional[List[dict]] = None) -> BrowserRunResult:
        if run_result.status == BrowserRunStatus.PASSED:
            run_result.error_type = None
            run_result.error_message = None
            return run_result

        # 1. Prioritize explicit network & console error logs if present
        if run_result.network_errors:
            run_result.error_type = BrowserFailureType.NETWORK_ERROR
            first_net = run_result.network_errors[0]
            url = first_net.get("url") if isinstance(first_net, dict) else getattr(first_net, "url", "")
            status_code = first_net.get("status_code") if isinstance(first_net, dict) else getattr(first_net, "status_code", 0)
            method = first_net.get("method") if isinstance(first_net, dict) else getattr(first_net, "method", "")
            run_result.error_message = f"Network request failed: {method} {url} ({status_code})"
        elif run_result.console_errors:
            run_result.error_type = BrowserFailureType.CONSOLE_ERROR
            first_console = run_result.console_errors[0]
            text = first_console.get("text") if isinstance(first_console, dict) else getattr(first_console, "text", "")
            run_result.error_message = f"Console error: {text}"
        else:
            # 2. Evaluate step results
            failed_step = next((s for s in run_result.step_results if s.status != BrowserRunStatus.PASSED), None)
            if failed_step:
                err_msg = (failed_step.error or "").lower()
                if "not found" in err_msg or "element" in err_msg or "selector" in err_msg:
                    run_result.error_type = BrowserFailureType.ELEMENT_NOT_FOUND
                elif "assertion" in err_msg or "expected" in err_msg:
                    run_result.error_type = BrowserFailureType.ASSERTION_FAILED
                elif "navigate" in err_msg or "net::" in err_msg or "connection refused" in err_msg:
                    run_result.error_type = BrowserFailureType.NAVIGATION_FAILED
                elif "timeout" in err_msg:
                    run_result.error_type = BrowserFailureType.TIMEOUT
                else:
                    run_result.error_type = BrowserFailureType.ASSERTION_FAILED

                run_result.error_message = failed_step.error or "Step assertion failed."
            elif run_result.status == BrowserRunStatus.TIMED_OUT:
                run_result.error_type = BrowserFailureType.TIMEOUT
                run_result.error_message = "Browser run execution timed out."
            elif run_result.status == BrowserRunStatus.BLOCKED:
                run_result.error_type = BrowserFailureType.BLOCKED_URL
                run_result.error_message = "Browser navigation blocked by security policy."
            else:
                run_result.error_type = BrowserFailureType.UNKNOWN
                run_result.error_message = "Unclassified browser failure."

        # Repository Correlation
        run_result.suspected_file = BrowserFailureClassifier._correlate_repository_file(run_result, repository_tree)
        return run_result

    @staticmethod
    def _correlate_repository_file(run_result: BrowserRunResult, repository_tree: Optional[List[dict]] = None) -> Optional[str]:
        if not repository_tree:
            return None

        # Extract URL paths or error locations
        candidate_paths = []

        for net in run_result.network_errors:
            url = net.get("url") if isinstance(net, dict) else getattr(net, "url", "")
            if url:
                url_path = url.split("://")[-1].split("/", 1)[-1]
                candidate_paths.append(url_path)

        for console in run_result.console_errors:
            loc = console.get("location") if isinstance(console, dict) else getattr(console, "location", None)
            if loc:
                candidate_paths.append(loc)

        for step in run_result.step_results:
            err = step.error if hasattr(step, "error") else step.get("error")
            if err:
                matches = re.findall(r'([a-zA-Z0-9_\-/]+\.[a-zA-Z0-9]+)', err)
                candidate_paths.extend(matches)

        # Match candidate paths against repository tree
        for candidate in candidate_paths:
            clean_cand = candidate.strip("/").lower()
            # Extract filename component, e.g. "api/v1/auth/login" -> "login" or "auth/login"
            parts = [p for p in clean_cand.split("/") if p]
            if not parts:
                continue
            leaf_part = parts[-1]  # e.g. "login" or "login.py"

            for tree_node in repository_tree:
                node_path = tree_node.get("path", "")
                clean_node = node_path.strip("/").lower()
                node_basename = clean_node.rsplit("/", 1)[-1].rsplit(".", 1)[0]  # "login" from "apps/api/app/api/login.py"

                if leaf_part and (leaf_part == node_basename or leaf_part in clean_node or clean_node in leaf_part):
                    return node_path

        return None

