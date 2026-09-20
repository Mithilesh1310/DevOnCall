from typing import Dict, Any
from app.services.agent.policies import ToolPermission
from app.services.agent.models import ToolResult
from app.services.agent.tools.base import BaseTool, ToolContext
from app.services.deployment.manager import DeploymentManager


class ReleaseCandidateStatusTool(BaseTool):
    """
    Queries release candidate status, approval state, and canary progress.
    Strictly READ_ONLY — does NOT trigger canary or deployment.
    """

    @property
    def name(self) -> str:
        return "release_candidate_status"

    @property
    def description(self) -> str:
        return "Queries status, approvals, canary progress, and deployment state of a release candidate. Strictly READ_ONLY."

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.READ_ONLY

    async def execute(self, input_params: Dict[str, Any], context: ToolContext) -> ToolResult:
        rc_id = input_params.get("rc_id") or "rc-demo-1"
        project_id = input_params.get("project_id", context.project_id)

        manager = DeploymentManager()
        rc_data = manager.get_release_candidate(rc_id)

        if not rc_data:
            # Fallback representation for query if missing
            return ToolResult(
                success=True,
                tool=self.name,
                data={
                    "rc_id": rc_id,
                    "project_id": project_id,
                    "status": "STAGING_PASSED",
                    "commit_sha": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
                    "staging_deployment_id": "stg-demo-1",
                    "approvals": [
                        {"type": "CANARY_RELEASE", "status": "APPROVED"},
                        {"type": "FULL_PRODUCTION", "status": "PENDING"}
                    ],
                    "canary_status": "NONE"
                }
            )

        return ToolResult(
            success=True,
            tool=self.name,
            data=rc_data.model_dump()
        )


class CanaryVerificationDetailsTool(BaseTool):
    """
    Queries detailed canary metrics, error rates, p95/p99 latency, and verdict.
    Strictly READ_ONLY — does NOT alter canary traffic or promote deployment.
    """

    @property
    def name(self) -> str:
        return "canary_verification_details"

    @property
    def description(self) -> str:
        return "Queries telemetry metrics, baseline vs candidate comparisons, and decision engine verdict for a canary deployment. Strictly READ_ONLY."

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.READ_ONLY

    async def execute(self, input_params: Dict[str, Any], context: ToolContext) -> ToolResult:
        canary_id = input_params.get("canary_id") or "canary-demo-1"
        scenario = input_params.get("scenario") or "HEALTHY"

        manager = DeploymentManager()
        verif_data = manager.get_canary_verification(canary_id, scenario=scenario)

        return ToolResult(
            success=True,
            tool=self.name,
            data=verif_data.model_dump()
        )


class DeploymentAuditLogTool(BaseTool):
    """
    Retrieves execution audit log events for a release candidate.
    Strictly READ_ONLY.
    """

    @property
    def name(self) -> str:
        return "deployment_audit_log"

    @property
    def description(self) -> str:
        return "Retrieves immutable audit trail logs for a release candidate including approvals, canary steps, and deployment state changes. Strictly READ_ONLY."

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.READ_ONLY

    async def execute(self, input_params: Dict[str, Any], context: ToolContext) -> ToolResult:
        rc_id = input_params.get("rc_id") or "rc-demo-1"

        manager = DeploymentManager()
        logs = manager.get_audit_logs(rc_id)

        return ToolResult(
            success=True,
            tool=self.name,
            data={
                "rc_id": rc_id,
                "audit_logs": logs,
                "total_events": len(logs)
            }
        )
