import pytest
from app.services.incident.stack_parser import ParsedStackFrame
from app.services.incident.correlator import RepositoryCorrelator

def test_correlator_exact_match():
    frames = [
        ParsedStackFrame(file="src/components/UserCard.tsx", line=20, column=5, function="UserCard", raw_frame=""),
    ]
    snapshot = {
        "tree": [
            {"path": "src/components/UserCard.tsx", "type": "file"},
            {"path": "src/index.tsx", "type": "file"}
        ]
    }

    matches = RepositoryCorrelator.correlate(frames, snapshot)
    assert len(matches) == 1
    assert matches[0].status == "MATCHED"
    assert matches[0].repository_file == "src/components/UserCard.tsx"
    assert matches[0].confidence == 1.0

def test_correlator_suffix_match():
    frames = [
        ParsedStackFrame(file="components/UserCard.tsx", line=20, function="UserCard", raw_frame=""),
    ]
    snapshot = {
        "tree": [
            {"path": "src/components/UserCard.tsx", "type": "file"},
        ]
    }

    matches = RepositoryCorrelator.correlate(frames, snapshot)
    assert len(matches) == 1
    assert matches[0].status == "MATCHED"
    assert matches[0].repository_file == "src/components/UserCard.tsx"

def test_correlator_unmatched():
    frames = [
        ParsedStackFrame(file="node_modules/express/lib/router.js", line=100, function="dispatch", raw_frame=""),
    ]
    snapshot = {
        "tree": [
            {"path": "src/index.ts", "type": "file"},
        ]
    }

    matches = RepositoryCorrelator.correlate(frames, snapshot)
    assert len(matches) == 1
    assert matches[0].status == "UNMATCHED"
    assert matches[0].repository_file is None
    assert matches[0].confidence == 0.0

def test_correlator_no_snapshot():
    frames = [
        ParsedStackFrame(file="app/main.py", line=10, function="main", raw_frame=""),
    ]
    matches = RepositoryCorrelator.correlate(frames, None)
    assert len(matches) == 1
    assert matches[0].status == "UNMATCHED"
