import pytest
from app.services.workspace import default_workspace_manager

def test_resolve_workspace_path_containment():
    run_id = "sec-run-01"

    # Valid relative path
    valid, abs_path, err = default_workspace_manager.resolve_workspace_path(run_id, "src/main.py")
    assert valid is True
    assert err is None
    assert "workspaces" in abs_path

    # Reject path traversal ../
    valid, abs_path, err = default_workspace_manager.resolve_workspace_path(run_id, "../../outside.txt")
    assert valid is False
    assert "Path traversal rejected" in err

    # Reject absolute path
    valid, abs_path, err = default_workspace_manager.resolve_workspace_path(run_id, "/etc/passwd")
    assert valid is False
    assert "Absolute paths are forbidden" in err

def test_resolve_workspace_path_protected_files():
    run_id = "sec-run-02"

    for forbidden in [".env", ".env.local", ".git/config", "id_rsa"]:
        valid, _, err = default_workspace_manager.resolve_workspace_path(run_id, forbidden)
        assert valid is False
        assert "Protected file access denied" in err
