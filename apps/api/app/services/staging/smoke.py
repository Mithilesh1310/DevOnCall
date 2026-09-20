import time
import urllib.request
from typing import List, Dict, Any, Optional
from app.services.staging.models import StagingCheckResult, StagingCheckType, StagingCheckStatus


ALLOWLISTED_SMOKE_ENDPOINTS = ["/", "/health", "/api/health", "/api/v1/status"]


class StagingSmokeTester:
    """
    Runs deterministic smoke tests against explicitly allowlisted staging endpoints.
    """

    def __init__(self, endpoints: Optional[List[str]] = None):
        self.endpoints = endpoints or ALLOWLISTED_SMOKE_ENDPOINTS

    def run_smoke_tests(self, deployment_id: str, deployment_url: str) -> StagingCheckResult:
        if not deployment_url:
            return StagingCheckResult(
                deployment_id=deployment_id,
                check_type=StagingCheckType.SMOKE,
                status=StagingCheckStatus.FAIL,
                duration_ms=0,
                summary="Smoke test failed: Deployment URL is empty",
            )

        start_time = time.time()
        passed_count = 0
        failed_count = 0
        endpoint_results = []

        for ep in self.endpoints:
            if ep not in ALLOWLISTED_SMOKE_ENDPOINTS:
                # Reject arbitrary unconfigured endpoints
                continue

            target_url = f"{deployment_url.rstrip('/')}{ep}"
            try:
                req = urllib.request.Request(target_url, headers={"User-Agent": "DevOnCall-StagingSmokeTester/1.0"})
                with urllib.request.urlopen(req, timeout=4) as resp:
                    code = resp.getcode()
                    if 200 <= code < 400:
                        passed_count += 1
                        endpoint_results.append({"endpoint": ep, "status": "PASS", "http_status": code})
                    else:
                        failed_count += 1
                        endpoint_results.append({"endpoint": ep, "status": "FAIL", "http_status": code})
            except Exception as e:
                # If endpoint not found 404, check if root / passed
                failed_count += 1
                endpoint_results.append({"endpoint": ep, "status": "FAIL", "error": str(e)})

        duration_ms = int((time.time() - start_time) * 1000)

        # Consider smoke test passed if at least 1 primary endpoint (e.g. / or /health) responds cleanly
        status = StagingCheckStatus.PASS if passed_count > 0 else StagingCheckStatus.FAIL
        summary = f"Smoke tests completed: {passed_count} PASSED, {failed_count} FAILED across {len(endpoint_results)} endpoints"

        return StagingCheckResult(
            deployment_id=deployment_id,
            check_type=StagingCheckType.SMOKE,
            status=status,
            duration_ms=duration_ms,
            summary=summary,
            details={"endpoints": endpoint_results, "passed": passed_count, "failed": failed_count},
        )
