import logging
from typing import List, Optional
from fastapi import APIRouter, Request, Header, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.session import get_db
from app.models.brain import ProjectBrainNodeModel, ProjectBrainEdgeModel, ProjectBrainEventModel
from app.schemas.brain import (
    BrainNodeResponse,
    BrainEdgeResponse,
    BrainEventResponse,
    BrainSummaryResponse,
    BrainQueryRequestSchema,
    BrainQueryResponseSchema,
)
from app.services.brain.manager import BrainManager
from app.services.brain.models import BrainNodeType

logger = logging.getLogger("devoncall.endpoints.brain")
router = APIRouter()


@router.get("/projects/{project_id}/brain", response_model=BrainQueryResponseSchema)
async def get_project_brain(project_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve all Brain nodes and relationships for a project."""
    manager = BrainManager()
    res = await manager.query(db, project_id, query_text="", limit=100)
    return BrainQueryResponseSchema(
        nodes=[BrainNodeResponse(**n.model_dump()) for n in res.nodes],
        edges=[BrainEdgeResponse(**e.model_dump()) for e in res.edges],
        events=[],
        total_count=res.total_count,
    )


@router.get("/projects/{project_id}/brain/summary", response_model=BrainSummaryResponse)
@router.get("/brain/summary", response_model=BrainSummaryResponse)
async def get_brain_summary(project_id: str = "demo-project", db: AsyncSession = Depends(get_db)):
    """Retrieve Project Brain summary metrics and confidence breakdown."""
    manager = BrainManager()
    sum_data = await manager.get_summary(db, project_id)
    return BrainSummaryResponse(**sum_data.model_dump())


@router.get("/brain/query", response_model=BrainQueryResponseSchema)
async def get_brain_query(project_id: str = "demo-project", query: str = "", limit: int = 20, db: AsyncSession = Depends(get_db)):
    """Query Project Brain via GET request."""
    manager = BrainManager()
    res = await manager.query(db, project_id, query_text=query, limit=limit)
    return BrainQueryResponseSchema(
        nodes=[BrainNodeResponse(**n.model_dump()) for n in res.nodes],
        edges=[BrainEdgeResponse(**e.model_dump()) for e in res.edges],
        events=[],
        total_count=res.total_count,
    )


@router.get("/brain/nodes", response_model=List[BrainNodeResponse])
async def get_brain_nodes_top(project_id: str = "demo-project", node_type: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """List Brain nodes via top-level GET request."""
    return await list_brain_nodes(project_id=project_id, node_type=node_type, db=db)


@router.get("/brain/history", response_model=List[BrainEventResponse])
async def get_brain_history_top(project_id: str = "demo-project", limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Retrieve Brain event history ledger via top-level GET request."""
    return await get_brain_history(project_id=project_id, limit=limit, db=db)


@router.get("/projects/{project_id}/brain/nodes", response_model=List[BrainNodeResponse])
async def list_brain_nodes(project_id: str, node_type: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """List Brain nodes filtered by project and optional node_type."""
    stmt = select(ProjectBrainNodeModel).where(ProjectBrainNodeModel.project_id == project_id)
    if node_type:
        stmt = stmt.where(ProjectBrainNodeModel.node_type == node_type.upper())

    res = await db.execute(stmt)
    nodes = res.scalars().all()
    return [
        BrainNodeResponse(
            id=n.id,
            project_id=n.project_id,
            node_type=n.node_type,
            key=n.key,
            title=n.title,
            content=n.content,
            source_type=n.source_type,
            source_reference=n.source_reference,
            confidence=n.confidence,
            status=n.status,
            metadata_payload=n.metadata_payload,
            created_at=n.created_at,
            updated_at=n.updated_at,
        )
        for n in nodes
    ]


@router.get("/projects/{project_id}/brain/nodes/{node_id}", response_model=BrainNodeResponse)
async def get_brain_node(project_id: str, node_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve single Brain node by ID."""
    res = await db.execute(select(ProjectBrainNodeModel).where(ProjectBrainNodeModel.id == node_id))
    n = res.scalar_one_or_none()
    if not n:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Brain node '{node_id}' not found.")
    return BrainNodeResponse(
        id=n.id,
        project_id=n.project_id,
        node_type=n.node_type,
        key=n.key,
        title=n.title,
        content=n.content,
        source_type=n.source_type,
        source_reference=n.source_reference,
        confidence=n.confidence,
        status=n.status,
        metadata_payload=n.metadata_payload,
        created_at=n.created_at,
        updated_at=n.updated_at,
    )


@router.get("/projects/{project_id}/brain/relationships", response_model=List[BrainEdgeResponse])
async def list_brain_relationships(project_id: str, db: AsyncSession = Depends(get_db)):
    """List all Brain edges for a project."""
    res = await db.execute(select(ProjectBrainEdgeModel).where(ProjectBrainEdgeModel.project_id == project_id))
    edges = res.scalars().all()
    return [
        BrainEdgeResponse(
            id=e.id,
            project_id=e.project_id,
            source_node_id=e.source_node_id,
            target_node_id=e.target_node_id,
            relation=e.relation,
            confidence=e.confidence,
            source_reference=e.source_reference,
            created_at=e.created_at,
        )
        for e in edges
    ]


@router.get("/projects/{project_id}/brain/incidents", response_model=List[BrainNodeResponse])
async def list_brain_incidents(project_id: str, db: AsyncSession = Depends(get_db)):
    """List Brain INCIDENT, ROOT_CAUSE, and FIX nodes."""
    res = await db.execute(
        select(ProjectBrainNodeModel).where(
            (ProjectBrainNodeModel.project_id == project_id)
            & (ProjectBrainNodeModel.node_type.in_(["INCIDENT", "ROOT_CAUSE", "FIX"]))
        )
    )
    nodes = res.scalars().all()
    return [
        BrainNodeResponse(
            id=n.id,
            project_id=n.project_id,
            node_type=n.node_type,
            key=n.key,
            title=n.title,
            content=n.content,
            source_type=n.source_type,
            source_reference=n.source_reference,
            confidence=n.confidence,
            status=n.status,
            metadata_payload=n.metadata_payload,
            created_at=n.created_at,
            updated_at=n.updated_at,
        )
        for n in nodes
    ]


@router.get("/projects/{project_id}/brain/history", response_model=List[BrainEventResponse])
async def get_brain_history(project_id: str, limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Retrieve Brain event history ledger."""
    res = await db.execute(
        select(ProjectBrainEventModel)
        .where(ProjectBrainEventModel.project_id == project_id)
        .order_by(ProjectBrainEventModel.created_at.desc())
        .limit(limit)
    )
    events = res.scalars().all()
    return [
        BrainEventResponse(
            id=e.id,
            project_id=e.project_id,
            event_type=e.event_type,
            source=e.source,
            summary=e.summary,
            payload=e.payload,
            created_at=e.created_at,
        )
        for e in events
    ]


@router.post("/projects/{project_id}/brain/rebuild")
async def rebuild_project_brain(project_id: str, db: AsyncSession = Depends(get_db)):
    """Rebuilds Brain nodes and edges from deterministic repository extraction."""
    mock_snapshot = {
        "repo_name": "DevOnCall",
        "repo_url": "https://github.com/owner/devoncall",
        "default_branch": "main",
        "commit_sha": "a1b2c3d4e5f67890",
        "tree": [
            {"path": "apps/api/app/main.py", "type": "blob"},
            {"path": "apps/web/src/app/page.tsx", "type": "blob"},
            {"path": "package.json", "type": "blob"},
            {"path": "pyproject.toml", "type": "blob"},
            {"path": "alembic/env.py", "type": "blob"},
        ],
    }
    manager = BrainManager()
    res = await manager.rebuild_from_repository(db, project_id, mock_snapshot)
    return res


@router.post("/projects/{project_id}/brain/query", response_model=BrainQueryResponseSchema)
async def query_project_brain(
    project_id: str,
    req: BrainQueryRequestSchema,
    db: AsyncSession = Depends(get_db),
):
    """Query Project Brain for architectural nodes, services, dependencies, and fixes."""
    manager = BrainManager()
    res = await manager.query(db, project_id, query_text=req.query, limit=req.limit)
    return BrainQueryResponseSchema(
        nodes=[BrainNodeResponse(**n.model_dump()) for n in res.nodes],
        edges=[BrainEdgeResponse(**e.model_dump()) for e in res.edges],
        events=[],
        total_count=res.total_count,
    )


@router.post("/projects/{project_id}/brain/refresh")
async def refresh_project_brain(project_id: str, db: AsyncSession = Depends(get_db)):
    """Refreshes Project Brain repository scan nodes."""
    manager = BrainManager()
    mock_snapshot = {
        "repo_name": "DevOnCall",
        "repo_url": "https://github.com/owner/devoncall",
        "default_branch": "main",
        "commit_sha": "a1b2c3d4e5f67890",
        "tree": [
            {"path": "apps/api/app/main.py", "type": "blob"},
            {"path": "apps/web/src/app/page.tsx", "type": "blob"},
        ],
    }
    return await manager.rebuild_from_repository(db, project_id, mock_snapshot)
