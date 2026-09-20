import pytest
from app.schemas.repository import RepositoryMetadata
from app.services.integrations.github.inspector import RepositoryInspector

def test_repository_inspector_deterministic_parsing():
    metadata = RepositoryMetadata(
        owner="mock-owner",
        repo="devoncall-demo",
        default_branch="main",
        commit_sha="a1b2c3d4e5f67890",
        html_url="https://github.com/mock-owner/devoncall-demo",
        is_private=False
    )

    raw_tree = [
        {"path": "package.json", "type": "blob", "size": 1000},
        {"path": "next.config.js", "type": "blob", "size": 200},
        {"path": "pyproject.toml", "type": "blob", "size": 500},
        {"path": "Dockerfile", "type": "blob", "size": 300},
        {"path": "docker-compose.yml", "type": "blob", "size": 400},
        {"path": "tsconfig.json", "type": "blob", "size": 350},
        {"path": "README.md", "type": "blob", "size": 1500},
        {"path": "node_modules/express/index.js", "type": "blob", "size": 9000}, # should be excluded
        {"path": ".git/HEAD", "type": "blob", "size": 50},                      # should be excluded
        {"path": "src", "type": "tree"},
        {"path": "src/app.ts", "type": "blob", "size": 800},
        {"path": "tests", "type": "tree"},
        {"path": "tests/test_main.py", "type": "blob", "size": 400},
    ]

    snapshot = RepositoryInspector.inspect(metadata, raw_tree)

    assert snapshot.owner == "mock-owner"
    assert snapshot.repo == "devoncall-demo"
    assert snapshot.total_files > 0
    
    # Excluded directories must NOT be in snapshot important files or tree
    all_snapshot_paths = [node.path for node in snapshot.tree]
    assert not any("node_modules" in p for p in all_snapshot_paths)
    assert not any(".git" in p for p in all_snapshot_paths)

    # Important files detection
    assert "package.json" in snapshot.important_files
    assert "pyproject.toml" in snapshot.important_files
    assert "Dockerfile" in snapshot.important_files

    # Source & Test directory detection
    assert "src" in snapshot.source_directories
    assert "tests" in snapshot.test_directories

    # Framework detection rules
    detection_names = [d.name for d in snapshot.detections]
    assert "Next.js" in detection_names
    assert "FastAPI" in detection_names
    assert "Node.js" in detection_names
    assert "Docker" in detection_names

    # Check status DETECTED vs INFERRED
    nextjs_det = next(d for d in snapshot.detections if d.name == "Next.js")
    assert nextjs_det.status == "DETECTED"
    assert nextjs_det.confidence == 1.0
