import pytest
from app.services.agent.tools.repository import RepositoryInfoTool, RepositoryTreeTool, ProjectSnapshotTool
from app.services.agent.tools.files import FileMetadataTool
from app.services.agent.tools.search import SearchRepositoryTool
from app.services.agent.tools.base import ToolContext

@pytest.fixture
def mock_context():
    return ToolContext(
        run_id="test-run",
        project_id="test-proj",
        repository_snapshot={
            "owner": "mock-owner",
            "repo": "devoncall-demo",
            "default_branch": "main",
            "commit_sha": "a1b2c3d4",
            "url": "https://github.com/mock-owner/devoncall-demo",
            "total_files": 10,
            "total_directories": 3,
            "detected_languages": ["Python", "TypeScript"],
            "detections": [{"name": "FastAPI", "status": "DETECTED"}],
            "important_files": ["pyproject.toml", "Dockerfile"],
            "source_directories": ["app"],
            "test_directories": ["tests"],
            "tree": [
                {"path": "pyproject.toml", "name": "pyproject.toml", "type": "file", "size": 500},
                {"path": "app", "name": "app", "type": "directory"},
                {"path": "app/main.py", "name": "main.py", "type": "file", "size": 1200}
            ]
        }
    )

@pytest.mark.asyncio
async def test_repository_info_tool(mock_context):
    tool = RepositoryInfoTool()
    res = await tool.execute({}, mock_context)
    assert res.success is True
    assert res.data["repo"] == "devoncall-demo"
    assert "FastAPI" in [d["name"] for d in res.data["detections"]]

@pytest.mark.asyncio
async def test_repository_tree_tool(mock_context):
    tool = RepositoryTreeTool()
    res = await tool.execute({"max_depth": 2}, mock_context)
    assert res.success is True
    assert res.data["total_items"] > 0

@pytest.mark.asyncio
async def test_file_metadata_tool(mock_context):
    tool = FileMetadataTool()
    res = await tool.execute({"path": "pyproject.toml"}, mock_context)
    assert res.success is True
    assert res.data["extension"] == ".toml"
    assert res.data["is_important_file"] is True

@pytest.mark.asyncio
async def test_search_repository_tool(mock_context):
    tool = SearchRepositoryTool()
    res = await tool.execute({"query": "main"}, mock_context)
    assert res.success is True
    assert res.data["total_matches"] >= 1

@pytest.mark.asyncio
async def test_project_snapshot_tool(mock_context):
    tool = ProjectSnapshotTool()
    res = await tool.execute({}, mock_context)
    assert res.success is True
    assert res.data["owner"] == "mock-owner"
