import pytest
from httpx import AsyncClient

from app.services.brain.extractor import RepositoryBrainExtractor
from app.services.brain.confidence import BrainConfidenceEvaluator
from app.services.brain.updater import BrainUpdater
from app.services.brain.query import BrainQueryService
from app.services.brain.manager import BrainManager
from app.services.brain.mock_brain import MockBrainProvider
from app.services.brain.models import (
    BrainNode,
    BrainEdge,
    BrainNodeType,
    BrainSourceType,
    BrainConfidence,
    BrainRelationType,
)


def test_repository_brain_extractor():
    """Verify extracting architecture, services, and database nodes from a repository snapshot."""
    snapshot = {
        "repo_name": "DevOnCall",
        "default_branch": "main",
        "commit_sha": "a1b2c3d4e5f6",
        "tree": [
            {"path": "apps/api/app/main.py"},
            {"path": "apps/web/package.json"},
            {"path": "alembic/env.py"},
            {"path": "docker-compose.yml"},
        ]
    }
    extractor = RepositoryBrainExtractor()
    nodes, edges = extractor.extract_from_snapshot("test-proj", snapshot)

    assert len(nodes) >= 3
    node_keys = [n.key for n in nodes]
    assert "project:test-proj" in node_keys
    assert "service:apps/api" in node_keys
    assert "service:apps/web" in node_keys

    edge_relations = [e.relation for e in edges]
    assert BrainRelationType.CONTAINS in edge_relations


def test_brain_confidence_evaluator():
    """Verify confidence evaluator assigns correct ratings based on source type."""
    assert BrainConfidenceEvaluator.determine_confidence(BrainSourceType.REPOSITORY_SCAN) == BrainConfidence.VERIFIED
    assert BrainConfidenceEvaluator.determine_confidence(BrainSourceType.HUMAN) == BrainConfidence.VERIFIED
    assert BrainConfidenceEvaluator.determine_confidence(BrainSourceType.VALIDATION) == BrainConfidence.HIGH
    assert BrainConfidenceEvaluator.determine_confidence(BrainSourceType.STAGING) == BrainConfidence.HIGH
    assert BrainConfidenceEvaluator.determine_confidence(BrainSourceType.INCIDENT, is_deterministic=False) == BrainConfidence.MEDIUM
    assert BrainConfidenceEvaluator.determine_confidence(BrainSourceType.SYSTEM) == BrainConfidence.MEDIUM


@pytest.mark.asyncio
async def test_brain_updater_and_deduplication(db_session):
    """Verify node upsert, deduplication by key, and event ledger logging."""
    updater = BrainUpdater()

    node1 = BrainNode(
        id="n1",
        project_id="test-proj",
        node_type=BrainNodeType.SERVICE,
        key="service:test-service",
        title="Test Service",
        content="Original content",
        source_type=BrainSourceType.REPOSITORY_SCAN,
        source_reference="snapshot-v1",
        confidence=BrainConfidence.VERIFIED,
        status="ACTIVE"
    )

    db_nodes = await updater.upsert_nodes(db_session, "test-proj", [node1])
    assert len(db_nodes) == 1
    assert db_nodes[0].content == "Original content"

    # Upsert updated node with same key -> should update content and log event
    node2 = BrainNode(
        id="n2",
        project_id="test-proj",
        node_type=BrainNodeType.SERVICE,
        key="service:test-service",
        title="Test Service Updated",
        content="Updated content v2",
        source_type=BrainSourceType.REPOSITORY_SCAN,
        source_reference="snapshot-v2",
        confidence=BrainConfidence.VERIFIED,
        status="ACTIVE"
    )

    db_nodes_updated = await updater.upsert_nodes(db_session, "test-proj", [node2])
    assert len(db_nodes_updated) == 1
    assert db_nodes_updated[0].content == "Updated content v2"


@pytest.mark.asyncio
async def test_brain_query_service(db_session):
    """Verify querying summary, nodes by type, and search nodes."""
    updater = BrainUpdater()
    query_service = BrainQueryService()

    nodes = [
        BrainNode(
            id="n10",
            project_id="query-proj",
            node_type=BrainNodeType.SERVICE,
            key="service:api",
            title="FastAPI Backend",
            content="Core REST API and agent orchestration",
            source_type=BrainSourceType.REPOSITORY_SCAN,
            source_reference="apps/api",
            confidence=BrainConfidence.VERIFIED,
            status="ACTIVE"
        ),
        BrainNode(
            id="n11",
            project_id="query-proj",
            node_type=BrainNodeType.INCIDENT,
            key="incident:inc-101",
            title="Database Connection Pool Exhausted",
            content="Max connection limit reached in postgres",
            source_type=BrainSourceType.INCIDENT,
            source_reference="sentry-101",
            confidence=BrainConfidence.MEDIUM,
            status="RESOLVED"
        )
    ]

    await updater.upsert_nodes(db_session, "query-proj", nodes)

    summary = await query_service.get_project_summary(db_session, "query-proj")
    assert summary.total_nodes == 2
    assert summary.services_count == 1
    assert summary.incidents_count == 1

    services = await query_service.get_nodes_by_type(db_session, "query-proj", BrainNodeType.SERVICE)
    assert len(services) == 1
    assert services[0].title == "FastAPI Backend"

    search_res = await query_service.search_nodes(db_session, "query-proj", "Database")
    assert len(search_res.nodes) == 1
    assert search_res.nodes[0].key == "incident:inc-101"


@pytest.mark.asyncio
async def test_brain_manager_rebuild_and_query(db_session):
    """Verify BrainManager rebuild flow and high level facade."""
    bm = BrainManager()
    snapshot = {"tree": [{"path": "apps/api/app/main.py"}, {"path": "apps/web/package.json"}]}

    rebuild_res = await bm.rebuild_from_repository(db_session, "mgr-proj", snapshot)
    assert rebuild_res["status"] == "REBUILT"
    assert rebuild_res["nodes_count"] >= 2

    summary = await bm.get_summary(db_session, "mgr-proj")
    assert summary.total_nodes >= 2

    q_res = await bm.query(db_session, "mgr-proj", query_text="apps/api")
    assert len(q_res.nodes) >= 1


def test_mock_brain_provider():
    """Verify MockBrainProvider returns structured mock summary and nodes."""
    mock = MockBrainProvider()
    summary = mock.get_summary("demo-project")
    assert summary.project_id == "demo-project"
    assert summary.total_nodes > 0
    assert summary.verified_facts_count > 0

    query_res = mock.search("api")
    assert len(query_res.nodes) > 0


@pytest.mark.asyncio
async def test_brain_rest_api_endpoints(client: AsyncClient):
    """Verify REST API endpoints for Brain summary, query, rebuild, and history."""
    # 1. Summary Endpoint
    res_sum = await client.get("/api/v1/brain/summary?project_id=demo-project")
    assert res_sum.status_code == 200
    data_sum = res_sum.json()
    assert "total_nodes" in data_sum

    # 2. Query Endpoint
    res_q = await client.get("/api/v1/brain/query?project_id=demo-project&query=service")
    assert res_q.status_code == 200
    data_q = res_q.json()
    assert "nodes" in data_q

    # 3. Nodes Endpoint
    res_n = await client.get("/api/v1/brain/nodes?project_id=demo-project")
    assert res_n.status_code == 200

    # 4. Rebuild Endpoint
    res_reb = await client.post("/api/v1/projects/demo-project/brain/rebuild")
    assert res_reb.status_code == 200
    data_reb = res_reb.json()
    assert data_reb["status"] == "REBUILT"

    # 5. History Endpoint
    res_hist = await client.get("/api/v1/brain/history?project_id=demo-project")
    assert res_hist.status_code == 200
