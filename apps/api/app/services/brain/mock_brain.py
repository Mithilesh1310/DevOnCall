from typing import Dict, Any, List
from app.services.brain.models import (
    BrainNode,
    BrainEdge,
    BrainEvent,
    BrainSummary,
    BrainNodeType,
    BrainSourceType,
    BrainConfidence,
    BrainRelationType,
    BrainQueryResponse,
)


class MockBrainProvider:
    """
    Deterministic Mock Brain Provider for testing DevOnCall Project Brain offline.
    """

    def __init__(self, project_id: str = "demo-project"):
        self.project_id = project_id
        self.nodes: List[BrainNode] = [
            BrainNode(
                id="node-proj-1",
                project_id=project_id,
                node_type=BrainNodeType.PROJECT,
                key=f"project:{project_id}",
                title=f"Project {project_id}",
                content="Monorepo repository structure for DevOnCall",
                source_type=BrainSourceType.REPOSITORY_SCAN,
                source_reference="repo_snapshot:a1b2c3d4",
                confidence=BrainConfidence.VERIFIED,
            ),
            BrainNode(
                id="node-svc-1",
                project_id=project_id,
                node_type=BrainNodeType.SERVICE,
                key="service:apps/api",
                title="Service FastApi Backend (apps/api)",
                content="Python FastAPI REST service framework",
                source_type=BrainSourceType.REPOSITORY_SCAN,
                source_reference="repo_snapshot:a1b2c3d4",
                confidence=BrainConfidence.VERIFIED,
            ),
            BrainNode(
                id="node-svc-2",
                project_id=project_id,
                node_type=BrainNodeType.SERVICE,
                key="service:apps/web",
                title="Service Next.js Web App (apps/web)",
                content="React Next.js frontend UI application",
                source_type=BrainSourceType.REPOSITORY_SCAN,
                source_reference="repo_snapshot:a1b2c3d4",
                confidence=BrainConfidence.VERIFIED,
            ),
            BrainNode(
                id="node-db-1",
                project_id=project_id,
                node_type=BrainNodeType.DATABASE,
                key="database:alembic_postgres",
                title="PostgreSQL Database & Alembic Migrations",
                content="SQLAlchemy 2.0 Async database schema",
                source_type=BrainSourceType.REPOSITORY_SCAN,
                source_reference="repo_snapshot:a1b2c3d4",
                confidence=BrainConfidence.VERIFIED,
            ),
        ]
        self.edges: List[BrainEdge] = [
            BrainEdge(
                id="edge-1",
                project_id=project_id,
                source_node_id="node-proj-1",
                target_node_id="node-svc-1",
                relation=BrainRelationType.CONTAINS,
                confidence=BrainConfidence.VERIFIED,
                source_reference="repo_snapshot:a1b2c3d4",
            ),
            BrainEdge(
                id="edge-2",
                project_id=project_id,
                source_node_id="node-proj-1",
                target_node_id="node-svc-2",
                relation=BrainRelationType.CONTAINS,
                confidence=BrainConfidence.VERIFIED,
                source_reference="repo_snapshot:a1b2c3d4",
            ),
        ]

    def get_summary(self, project_id: Optional[str] = None) -> BrainSummary:
        pid = project_id or self.project_id
        return BrainSummary(
            project_id=pid,
            total_nodes=len(self.nodes),
            total_edges=len(self.edges),
            verified_facts_count=4,
            services_count=2,
            incidents_count=0,
            deployments_count=0,
            node_type_breakdown={"PROJECT": 1, "SERVICE": 2, "DATABASE": 1},
            source_type_breakdown={"REPOSITORY_SCAN": 4},
        )

    def search(self, query: str = "") -> BrainQueryResponse:
        matching = [n for n in self.nodes if not query or query.lower() in n.title.lower() or query.lower() in n.content.lower()]
        return BrainQueryResponse(nodes=matching, edges=self.edges, total_count=len(matching))
