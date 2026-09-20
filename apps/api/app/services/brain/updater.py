import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.brain import ProjectBrainNodeModel, ProjectBrainEdgeModel, ProjectBrainEventModel
from app.services.brain.models import (
    BrainNode,
    BrainEdge,
    BrainEvent,
    BrainNodeType,
    BrainSourceType,
    BrainConfidence,
    BrainRelationType,
)
from app.services.brain.provenance import BrainSecretRedactor

logger = logging.getLogger("devoncall.brain.updater")


class BrainUpdater:
    """
    Handles node/edge deduplication, conflict preservation, provenance attachment,
    and event ledger generation for repository scans, incidents, validations, and staging deployments.
    """

    @staticmethod
    async def upsert_nodes(db: AsyncSession, project_id: str, nodes: List[BrainNode]) -> List[ProjectBrainNodeModel]:
        saved_models = []
        now_utc = datetime.now(timezone.utc)

        for node in nodes:
            redacted_title = BrainSecretRedactor.redact_text(node.title)
            redacted_content = BrainSecretRedactor.redact_text(node.content)
            redacted_metadata = BrainSecretRedactor.redact_dict(node.metadata_payload)

            # Deduplication check by project_id and key
            res = await db.execute(
                select(ProjectBrainNodeModel).where(
                    (ProjectBrainNodeModel.project_id == project_id) & (ProjectBrainNodeModel.key == node.key)
                )
            )
            existing = res.scalar_one_or_none()

            if existing:
                # Update existing node cleanly while preserving provenance history
                existing.title = redacted_title
                existing.content = redacted_content
                existing.confidence = node.confidence.value
                existing.metadata_payload = redacted_metadata
                existing.updated_at = now_utc
                saved_models.append(existing)

                # Append event ledger
                evt = ProjectBrainEventModel(
                    project_id=project_id,
                    event_type="FACT_UPDATED",
                    source=node.source_type.value,
                    summary=f"Updated node '{node.key}' ({node.node_type.value})",
                    payload={"node_id": existing.id, "key": node.key},
                )
                db.add(evt)
            else:
                db_node = ProjectBrainNodeModel(
                    id=node.id,
                    project_id=project_id,
                    node_type=node.node_type.value,
                    key=node.key,
                    title=redacted_title,
                    content=redacted_content,
                    source_type=node.source_type.value,
                    source_reference=node.source_reference,
                    confidence=node.confidence.value,
                    status=node.status,
                    metadata_payload=redacted_metadata,
                )
                db.add(db_node)
                saved_models.append(db_node)

                evt = ProjectBrainEventModel(
                    project_id=project_id,
                    event_type="NODE_CREATED",
                    source=node.source_type.value,
                    summary=f"Created node '{node.key}' ({node.node_type.value})",
                    payload={"node_id": db_node.id, "key": node.key},
                )
                db.add(evt)

        await db.commit()
        return saved_models

    @staticmethod
    async def add_edges(db: AsyncSession, project_id: str, edges: List[BrainEdge]) -> List[ProjectBrainEdgeModel]:
        saved_edges = []
        for edge in edges:
            # Check edge duplication
            res = await db.execute(
                select(ProjectBrainEdgeModel).where(
                    (ProjectBrainEdgeModel.project_id == project_id)
                    & (ProjectBrainEdgeModel.source_node_id == edge.source_node_id)
                    & (ProjectBrainEdgeModel.target_node_id == edge.target_node_id)
                    & (ProjectBrainEdgeModel.relation == edge.relation.value)
                )
            )
            existing = res.scalar_one_or_none()

            if not existing:
                db_edge = ProjectBrainEdgeModel(
                    id=edge.id,
                    project_id=project_id,
                    source_node_id=edge.source_node_id,
                    target_node_id=edge.target_node_id,
                    relation=edge.relation.value,
                    confidence=edge.confidence.value,
                    source_reference=edge.source_reference,
                )
                db.add(db_edge)
                saved_edges.append(db_edge)

        await db.commit()
        return saved_edges

    @staticmethod
    async def record_incident_knowledge(
        db: AsyncSession,
        project_id: str,
        incident_id: str,
        title: str,
        error_type: str,
        root_cause_summary: str,
        fix_summary: Optional[str] = None,
    ) -> Dict[str, Any]:
        source_ref = f"incident:{incident_id}"

        # 1. INCIDENT node
        inc_node = BrainNode(
            project_id=project_id,
            node_type=BrainNodeType.INCIDENT,
            key=f"incident:{incident_id}",
            title=f"Incident #{incident_id[:8]}: {error_type}",
            content=f"Title: {title}\nType: {error_type}",
            source_type=BrainSourceType.INCIDENT,
            source_reference=source_ref,
            confidence=BrainConfidence.HIGH,
        )

        # 2. ROOT_CAUSE node
        rc_node = BrainNode(
            project_id=project_id,
            node_type=BrainNodeType.ROOT_CAUSE,
            key=f"root_cause:{incident_id}",
            title=f"Root Cause for #{incident_id[:8]}",
            content=root_cause_summary,
            source_type=BrainSourceType.INCIDENT,
            source_reference=source_ref,
            confidence=BrainConfidence.HIGH,
        )

        nodes = [inc_node, rc_node]
        edges = [
            BrainEdge(
                project_id=project_id,
                source_node_id=inc_node.id,
                target_node_id=rc_node.id,
                relation=BrainRelationType.CAUSED_BY,
                confidence=BrainConfidence.HIGH,
                source_reference=source_ref,
            )
        ]

        if fix_summary:
            fix_node = BrainNode(
                project_id=project_id,
                node_type=BrainNodeType.FIX,
                key=f"fix:{incident_id}",
                title=f"Fix for #{incident_id[:8]}",
                content=fix_summary,
                source_type=BrainSourceType.INCIDENT,
                source_reference=source_ref,
                confidence=BrainConfidence.HIGH,
            )
            nodes.append(fix_node)
            edges.append(
                BrainEdge(
                    project_id=project_id,
                    source_node_id=rc_node.id,
                    target_node_id=fix_node.id,
                    relation=BrainRelationType.FIXED_BY,
                    confidence=BrainConfidence.HIGH,
                    source_reference=source_ref,
                )
            )

        await BrainUpdater.upsert_nodes(db, project_id, nodes)
        await BrainUpdater.add_edges(db, project_id, edges)
        return {"incident_id": incident_id, "nodes_created": len(nodes)}

    @staticmethod
    async def record_staging_knowledge(
        db: AsyncSession,
        project_id: str,
        deployment_id: str,
        commit_sha: str,
        branch: str,
        status: str,
        url: str,
    ) -> Dict[str, Any]:
        source_ref = f"staging:{deployment_id}"

        stg_node = BrainNode(
            project_id=project_id,
            node_type=BrainNodeType.DEPLOYMENT,
            key=f"staging:{deployment_id}",
            title=f"Staging Deployment #{deployment_id[:8]}",
            content=f"Branch: {branch}\nCommit: {commit_sha[:8]}\nStatus: {status}\nURL: {url}",
            source_type=BrainSourceType.STAGING,
            source_reference=source_ref,
            confidence=BrainConfidence.HIGH,
            metadata_payload={"commit_sha": commit_sha, "branch": branch, "status": status, "url": url},
        )

        await BrainUpdater.upsert_nodes(db, project_id, [stg_node])
        return {"deployment_id": deployment_id, "status": status}
