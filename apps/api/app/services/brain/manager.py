import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.brain.extractor import RepositoryBrainExtractor
from app.services.brain.updater import BrainUpdater
from app.services.brain.query import BrainQueryService
from app.services.brain.models import BrainSummary, BrainQueryResponse, BrainNodeType

logger = logging.getLogger("devoncall.brain.manager")


class BrainManager:
    """
    High-level facade orchestrating Project Brain extraction, deduplication,
    event tracking, query processing, and persistent database operations.
    """

    def __init__(self):
        self.extractor = RepositoryBrainExtractor()
        self.updater = BrainUpdater()
        self.query_service = BrainQueryService()

    async def rebuild_from_repository(self, db: AsyncSession, project_id: str, repo_snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Runs deterministic repository scan and updates Brain nodes and edges."""
        logger.info(f"Rebuilding Project Brain for project '{project_id}' from repository snapshot...")
        nodes, edges = self.extractor.extract_from_snapshot(project_id, repo_snapshot)

        db_nodes = await self.updater.upsert_nodes(db, project_id, nodes)
        db_edges = await self.updater.add_edges(db, project_id, edges)

        return {
            "status": "REBUILT",
            "project_id": project_id,
            "nodes_count": len(db_nodes),
            "edges_count": len(db_edges),
        }

    async def get_summary(self, db: AsyncSession, project_id: str) -> BrainSummary:
        return await self.query_service.get_project_summary(db, project_id)

    async def query(self, db: AsyncSession, project_id: str, query_text: str = "", limit: int = 20) -> BrainQueryResponse:
        return await self.query_service.search_nodes(db, project_id, query_text, limit=limit)
