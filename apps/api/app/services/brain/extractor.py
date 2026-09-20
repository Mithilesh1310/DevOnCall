import os
import json
import logging
from typing import List, Tuple, Dict, Any
from app.services.brain.models import (
    BrainNode,
    BrainEdge,
    BrainNodeType,
    BrainSourceType,
    BrainConfidence,
    BrainRelationType,
)

logger = logging.getLogger("devoncall.brain.extractor")


class RepositoryBrainExtractor:
    """
    Consumes Phase 1 Repository Snapshot intelligence and extracts deterministic
    architectural nodes, services, dependencies, database structures, and relationships.
    """

    @staticmethod
    def extract_from_snapshot(project_id: str, repo_snapshot: Dict[str, Any]) -> Tuple[List[BrainNode], List[BrainEdge]]:
        nodes: List[BrainNode] = []
        edges: List[BrainEdge] = []

        repo_name = repo_snapshot.get("repo_name", "devoncall")
        source_ref = f"repo_snapshot:{repo_snapshot.get('commit_sha', 'head')[:8]}"

        # 1. Root PROJECT Node
        proj_node = BrainNode(
            project_id=project_id,
            node_type=BrainNodeType.PROJECT,
            key=f"project:{project_id}",
            title=f"Project {repo_name}",
            content=f"GitHub Repository: {repo_snapshot.get('repo_url', 'N/A')} (Default branch: {repo_snapshot.get('default_branch', 'main')})",
            source_type=BrainSourceType.REPOSITORY_SCAN,
            source_reference=source_ref,
            confidence=BrainConfidence.VERIFIED,
            metadata_payload={
                "owner": repo_snapshot.get("owner"),
                "repo_name": repo_name,
                "default_branch": repo_snapshot.get("default_branch"),
            },
        )
        nodes.append(proj_node)

        tree = repo_snapshot.get("tree", [])

        # 2. Extract Services (e.g. apps/api, apps/web)
        service_paths = set()
        for item in tree:
            path = item.get("path", "")
            if path.startswith("apps/") or path.startswith("packages/") or path.startswith("services/"):
                parts = path.split("/")
                if len(parts) >= 2:
                    svc_path = f"{parts[0]}/{parts[1]}"
                    service_paths.add(svc_path)

        for svc_path in sorted(service_paths):
            svc_name = svc_path.split("/")[-1]
            svc_node = BrainNode(
                project_id=project_id,
                node_type=BrainNodeType.SERVICE,
                key=f"service:{svc_path}",
                title=f"Service {svc_name} ({svc_path})",
                content=f"Monorepo service directory at {svc_path}",
                source_type=BrainSourceType.REPOSITORY_SCAN,
                source_reference=source_ref,
                confidence=BrainConfidence.VERIFIED,
                metadata_payload={"path": svc_path},
            )
            nodes.append(svc_node)

            # Edge: PROJECT -> CONTAINS -> SERVICE
            edges.append(
                BrainEdge(
                    project_id=project_id,
                    source_node_id=proj_node.id,
                    target_node_id=svc_node.id,
                    relation=BrainRelationType.CONTAINS,
                    confidence=BrainConfidence.VERIFIED,
                    source_reference=source_ref,
                )
            )

        # 3. Extract Database & Migrations
        db_found = any("alembic" in item.get("path", "") or "migrations" in item.get("path", "") for item in tree)
        if db_found:
            db_node = BrainNode(
                project_id=project_id,
                node_type=BrainNodeType.DATABASE,
                key="database:alembic_postgres",
                title="PostgreSQL Database & Alembic Migrations",
                content="SQLAlchemy 2.0 Async database schema managed via Alembic migrations",
                source_type=BrainSourceType.REPOSITORY_SCAN,
                source_reference=source_ref,
                confidence=BrainConfidence.VERIFIED,
                metadata_payload={"engine": "postgresql", "migration_tool": "alembic"},
            )
            nodes.append(db_node)
            edges.append(
                BrainEdge(
                    project_id=project_id,
                    source_node_id=proj_node.id,
                    target_node_id=db_node.id,
                    relation=BrainRelationType.DEPENDS_ON,
                    confidence=BrainConfidence.VERIFIED,
                    source_reference=source_ref,
                )
            )

        # 4. Extract Package Manifests & Dependencies
        for item in tree:
            path = item.get("path", "")
            if path in ["package.json", "pyproject.toml", "requirements.txt"] or path.endswith("/package.json") or path.endswith("/pyproject.toml"):
                dep_node = BrainNode(
                    project_id=project_id,
                    node_type=BrainNodeType.DEPENDENCY,
                    key=f"manifest:{path}",
                    title=f"Dependency Manifest {path}",
                    content=f"Manifest file {path} specifying project dependencies",
                    source_type=BrainSourceType.REPOSITORY_SCAN,
                    source_reference=source_ref,
                    confidence=BrainConfidence.VERIFIED,
                    metadata_payload={"path": path},
                )
                nodes.append(dep_node)
                edges.append(
                    BrainEdge(
                        project_id=project_id,
                        source_node_id=proj_node.id,
                        target_node_id=dep_node.id,
                        relation=BrainRelationType.CONTAINS,
                        confidence=BrainConfidence.VERIFIED,
                        source_reference=source_ref,
                    )
                )

        logger.info(f"Extracted {len(nodes)} Brain nodes and {len(edges)} Brain edges for project '{project_id}'")
        return nodes, edges
