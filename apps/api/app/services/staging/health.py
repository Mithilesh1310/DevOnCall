import time
import urllib.request
from typing import Optional, Dict, Any
from app.services.staging.models import StagingCheckResult, StagingCheckType, StagingCheckStatus


class StagingHealthChecker:
    """
    Polls the staging health endpoint until readiness or timeout.
    """

    def __init__(self, timeout_seconds: int = 60, poll_interval_seconds: float = 1.0):
        self.timeout_seconds = timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds

    def check_health(self, deployment_id: str, deployment_url: str, health_path: str = "/health") -> StagingCheckResult:
        if not deployment_url:
            return StagingCheckResult(
                deployment_id=deployment_id,
                check_type=StagingCheckType.HEALTH,
                status=StagingCheckStatus.FAIL,
                duration_ms=0,
                summary="Health check failed: Deployment URL is empty",
            )

        target_url = f"{deployment_url.rstrip('/')}{health_path}"
        start_time = time.time()
        deadline = start_time + self.timeout_seconds

        while time.time() < deadline:
            try:
                req = urllib.request.Request(target_url, headers={"User-Agent": "DevOnCall-StagingHealthChecker/1.0"})
                with urllib.request.urlopen(req, timeout=3) as resp:
                    status_code = resp.getcode()
                    duration_ms = int((time.time() - start_time) * 1000)
                    if 200 <= status_code < 300:
                        return StagingCheckResult(
                            deployment_id=deployment_id,
                            check_type=StagingCheckType.HEALTH,
                            status=StagingCheckStatus.PASS,
                            duration_ms=duration_ms,
                            summary=f"Health check passed: GET {health_path} HTTP {status_code} ({duration_ms}ms)",
                            details={"http_status": status_code, "response_time_ms": duration_ms, "url": target_url},
                        )
            except Exception:
                pass

            time.sleep(self.poll_interval_seconds)

        elapsed_ms = int((time.time() - start_time) * 1000)
        return StagingCheckResult(
            deployment_id=deployment_id,
            check_type=StagingCheckType.HEALTH,
            status=StagingCheckStatus.FAIL,
            duration_ms=elapsed_ms,
            summary=f"Health check timed out after {self.timeout_seconds}s waiting for {target_url}",
            details={"timeout_seconds": self.timeout_seconds},
        )
