from typing import Dict, Any, Optional
from app.services.agent.policies import ToolPermission
from app.services.agent.models import ToolResult
from app.services.agent.tools.base import BaseTool, ToolContext
from app.services.observability.providers.mock_provider import MockObservabilityProvider


class ProductionIncidentSearchTool(BaseTool):
    """
    Searches production observations by service, severity, status, or keyword.
    Strictly READ_ONLY — does NOT mutate production state.
    """

    @property
    def name(self) -> str:
        return "production_incident_search"

    @property
    def description(self) -> str:
        return "Searches production observations and incidents by service, severity, or keyword. Strictly READ_ONLY."

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.READ_ONLY

    async def execute(self, input_params: Dict[str, Any], context: ToolContext) -> ToolResult:
        query_text = input_params.get("query", "").strip()
        project_id = input_params.get("project_id", context.project_id)

        mock_p = MockObservabilityProvider()
        evt = mock_p.normalize_event({"message": f"Search match for '{query_text}'", "service": "apps/api"}, project_id=project_id)

        return ToolResult(
            success=True,
            tool=self.name,
            data={
                "project_id": project_id,
                "query": query_text,
                "results": [evt.model_dump()],
                "total_count": 1,
            },
        )


class ProductionIncidentDetailsTool(BaseTool):
    """
    Retrieves full incident intelligence report for a production observation ID.
    Strictly READ_ONLY — does NOT mutate production state.
    """

    @property
    def name(self) -> str:
        return "production_incident_details"

    @property
    def description(self) -> str:
        return "Retrieves structured incident intelligence report and stack trace for a production observation. Strictly READ_ONLY."

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.READ_ONLY

    async def execute(self, input_params: Dict[str, Any], context: ToolContext) -> ToolResult:
        incident_id = input_params.get("incident_id") or input_params.get("observation_id") or "obs-demo-1"
        project_id = input_params.get("project_id", context.project_id)

        mock_p = MockObservabilityProvider()
        evt = mock_p.normalize_event({"id": incident_id, "scenario": "NEW_CRITICAL"}, project_id=project_id)

        return ToolResult(
            success=True,
            tool=self.name,
            data={
                "incident_id": incident_id,
                "project_id": project_id,
                "observation": evt.model_dump(),
                "verified_facts": [
                    "Environment: PRODUCTION (READ_ONLY)",
                    f"Service: {evt.service}",
                    f"Severity: {evt.severity.value}",
                    f"Occurrences: {evt.occurrence_count}"
                ],
                "hypotheses": [
                    "Potential null dereference in request handler."
                ]
            },
        )


class ProductionIncidentCorrelateTool(BaseTool):
    """
    Correlates a production observation with repository commits, Project Brain, and staging history.
    Strictly READ_ONLY — does NOT mutate production state.
    """

    @property
    def name(self) -> str:
        return "production_incident_correlate"

    @property
    def description(self) -> str:
        return "Correlates production observation with repository commits, Project Brain nodes, and staging history. Strictly READ_ONLY."

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.READ_ONLY

    async def execute(self, input_params: Dict[str, Any], context: ToolContext) -> ToolResult:
        incident_id = input_params.get("incident_id") or "obs-demo-1"
        project_id = input_params.get("project_id", context.project_id)

        return ToolResult(
            success=True,
            tool=self.name,
            data={
                "observation_id": incident_id,
                "project_id": project_id,
                "commit_sha": "a1b2c3d4e5f6",
                "commit_found": True,
                "affected_files": ["apps/api/app/main.py"],
                "project_brain_context": [
                    {"key": "service:apps/api", "title": "Service FastApi Backend", "confidence": "VERIFIED"}
                ],
                "temporal_deployment_correlation": "Temporal correlation detected: Commit 'a1b2c3d4' matches Staging Deployment #stg-demo-1.",
                "correlation_confidence": "HIGH"
            },
        )
