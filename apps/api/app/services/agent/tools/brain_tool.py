from typing import Dict, Any, Optional
from app.services.agent.policies import ToolPermission
from app.services.agent.models import ToolResult, ToolError
from app.services.agent.tools.base import BaseTool, ToolContext
from app.services.brain.mock_brain import MockBrainProvider


class ProjectBrainQueryTool(BaseTool):
    """
    Queries DevOnCall Project Brain for architectural nodes, services, dependencies,
    known incidents, fixes, and validation history with complete provenance.
    Strictly READ_ONLY - cannot modify Brain state.
    """

    @property
    def name(self) -> str:
        return "project_brain_query"

    @property
    def description(self) -> str:
        return "Queries Project Brain for architectural knowledge, services, dependencies, previous incidents, and fixes with provenance."

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.READ_ONLY

    async def execute(self, input_params: Dict[str, Any], context: ToolContext) -> ToolResult:
        query_text = input_params.get("query", "").strip()
        project_id = input_params.get("project_id", "demo-project")

        # Mock brain provider query runner for tool context
        mock_provider = MockBrainProvider(project_id=project_id)
        res = mock_provider.search(query=query_text)

        nodes_out = [
            {
                "id": n.id,
                "node_type": n.node_type.value,
                "key": n.key,
                "title": n.title,
                "content": n.content,
                "source_type": n.source_type.value,
                "source_reference": n.source_reference,
                "confidence": n.confidence.value,
            }
            for n in res.nodes
        ]

        return ToolResult(
            success=True,
            tool=self.name,
            data={
                "project_id": project_id,
                "query": query_text,
                "nodes": nodes_out,
                "total_count": len(nodes_out),
            },
        )
