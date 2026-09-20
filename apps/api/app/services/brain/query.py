import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.models.brain import ProjectBrainNodeModel, ProjectBrainEdgeModel, ProjectBrainEventModel
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

logger = logging.getLogger("devoncall.brain.query")


class BrainQueryService:
    """
    Query Engine for Project Brain. Supports architecture lookups, service queries,
    dependency graphs, incident/fix history, search, and event ledger summaries with full provenance.
    """

    @staticmethod
    async def get_project_summary(db: AsyncSession, project_id: str) -> BrainSummary:
        nodes_res = await db.execute(select(ProjectBrainNodeModel).where(ProjectBrainNodeModel.project_id == project_id))
        nodes = nodes_res.scalars().all()

        edges_res = await db.execute(select(func.count(ProjectBrainEdgeModel.id)).where(ProjectBrainEdgeModel.project_id == project_id))
        total_edges = edges_res.scalar() or 0

        verified_count = sum(1 for n in nodes if n.confidence == "VERIFIED")
        services_count = sum(1 for n in nodes if n.node_type == "SERVICE")
        incidents_count = sum(1 for n in nodes if n.node_type == "INCIDENT")
        deployments_count = sum(1 for n in nodes if n.node_type == "DEPLOYMENT")

        node_type_breakdown = {}
        source_type_breakdown = {}

        for n in nodes:
            node_type_breakdown[n.node_type] = node_type_breakdown.get(n.node_type, 0) + 1
            source_type_breakdown[n.source_type] = source_type_breakdown.get(n.source_type, 0) + 1

        return BrainSummary(
            project_id=project_id,
            total_nodes=len(nodes),
            total_edges=total_edges,
            verified_facts_count=verified_count,
            services_count=services_count,
            incidents_count=incidents_count,
            deployments_count=deployments_count,
            node_type_breakdown=node_type_breakdown,
            source_type_breakdown=source_type_breakdown,
        )

    @staticmethod
    async def get_nodes_by_type(db: AsyncSession, project_id: str, node_type: BrainNodeType) -> List[BrainNode]:
        res = await db.execute(
            select(ProjectBrainNodeModel).where(
                (ProjectBrainNodeModel.project_id == project_id) & (ProjectBrainNodeModel.node_type == node_type.value)
            )
        )
        models = res.scalars().all()
        return [
            BrainNode(
                id=m.id,
                project_id=m.project_id,
                node_type=BrainNodeType(m.node_type),
                key=m.key,
                title=m.title,
                content=m.content,
                source_type=BrainSourceType(m.source_type),
                source_reference=m.source_reference,
                confidence=BrainConfidence(m.confidence),
                status=m.status,
                metadata_payload=m.metadata_payload,
                created_at=m.created_at.isoformat(),
                updated_at=m.updated_at.isoformat(),
            )
            for m in models
        ]

    @staticmethod
    async def search_nodes(db: AsyncSession, project_id: str, query: str, limit: int = 20) -> BrainQueryResponse:
        q_pattern = f"%{query.strip()}%" if query else "%"
        res = await db.execute(
            select(ProjectBrainNodeModel)
            .where(
                (ProjectBrainNodeModel.project_id == project_id)
                & (
                    (ProjectBrainNodeModel.title.like(q_pattern))
                    | (ProjectBrainNodeModel.content.like(q_pattern))
                    | (ProjectBrainNodeModel.key.like(q_pattern))
                )
            )
            .limit(limit)
        )
        models = res.scalars().all()

        nodes = [
            BrainNode(
                id=m.id,
                project_id=m.project_id,
                node_type=BrainNodeType(m.node_type),
                key=m.key,
                title=m.title,
                content=m.content,
                source_type=BrainSourceType(m.source_type),
                source_reference=m.source_reference,
                confidence=BrainConfidence(m.confidence),
                status=m.status,
                metadata_payload=m.metadata_payload,
                created_at=m.created_at.isoformat(),
                updated_at=m.updated_at.isoformat(),
            )
            for m in models
        ]

        # Fetch edges connecting these nodes
        node_ids = [n.id for n in nodes]
        edges_out = []
        if node_ids:
            edges_res = await db.execute(
                select(ProjectBrainEdgeModel).where(
                    (ProjectBrainEdgeModel.project_id == project_id)
                    & (
                        (ProjectBrainEdgeModel.source_node_id.in_(node_ids))
                        | (ProjectBrainEdgeModel.target_node_id.in_(node_ids))
                    )
                )
            )
            e_models = edges_res.scalars().all()
            edges_out = [
                BrainEdge(
                    id=e.id,
                    project_id=e.project_id,
                    source_node_id=e.source_node_id,
                    target_node_id=e.target_node_id,
                    relation=BrainRelationType(e.relation),
                    confidence=BrainConfidence(e.confidence),
                    source_reference=e.source_reference,
                    created_at=e.created_at.isoformat(),
                )
                for e in e_models
            ]

        return BrainQueryResponse(nodes=nodes, edges=edges_out, total_count=len(nodes))

    @staticmethod
    async def get_brain_history(db: AsyncSession, project_id: str, limit: int = 50) -> List[BrainEvent]:
        res = await db.execute(
            select(ProjectBrainEventModel)
            .where(ProjectBrainEventModel.project_id == project_id)
            .order_by(ProjectBrainEventModel.created_at.desc())
            .limit(limit)
        )
        events = res.scalars().all()
        return [
            BrainEvent(
                id=e.id,
                project_id=e.project_id,
                event_type=e.event_type,
                source=e.source,
                summary=e.summary,
                payload=e.payload,
                created_at=e.created_at.isoformat(),
            )
            for e in events
        ]
