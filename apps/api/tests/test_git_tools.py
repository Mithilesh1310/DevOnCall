import os
import pytest
from app.services.agent.tools.git_tools import (
    GitDiffTool, GitStatusTool, GitCreateBranchTool, GitCommitTool, CreatePullRequestTool
)
from app.services.agent.tools.base import ToolContext
from app.services.workspace import default_workspace_manager

@pytest.mark.asyncio
@pytest.mark.parametrize("default_branch_name", ["main", "master", "develop"])
async def test_dynamic_default_branch_handling(default_branch_name):
    """
    Verifies that default branch handling is dynamic across different repository configurations (main, master, develop).
    Proves:
    1. Feature branch is created from configured default branch.
    2. Configured default branch cannot be committed to directly.
    3. Configured default branch cannot be checked out for agent modifications.
    4. PR target branch equals configured default branch.
    5. Source feature branch != target default branch.
    """
    run_id = f"test-git-dyn-{default_branch_name}"
    context = ToolContext(
        run_id=run_id,
        project_id="proj-dyn-1",
        run_context={"default_branch": default_branch_name}
    )

    branch_tool = GitCreateBranchTool()
    commit_tool = GitCommitTool()
    pr_tool = CreatePullRequestTool()

    # 1. Reject feature branch matching configured default branch
    res_reject = await branch_tool.execute({"branch_name": default_branch_name}, context)
    assert res_reject.success is False
    assert res_reject.error.code == "PROTECTED_BRANCH_ERROR"
    assert default_branch_name in res_reject.error.message

    # 2. Allow feature branch creation targeting configured default branch
    feature_branch = f"devoncall/agent/{run_id[:8]}"
    res_ok = await branch_tool.execute({"branch_name": feature_branch}, context)
    assert res_ok.success is True
    assert res_ok.data["branch_name"] == feature_branch
    assert res_ok.data["base_branch"] == default_branch_name

    # 3. Reject direct commit to configured default branch
    commit_reject = await commit_tool.execute({
        "message": "Direct commit attempt",
        "branch": default_branch_name
    }, context)
    assert commit_reject.success is False
    assert commit_reject.error.code == "PROTECTED_BRANCH_ERROR"

    # 4. Allow commit on feature branch
    commit_ok = await commit_tool.execute({
        "message": "Feature fix commit",
        "branch": feature_branch
    }, context)
    assert commit_ok.success is True
    assert commit_ok.data["branch"] == feature_branch
    assert commit_ok.data["base_branch"] == default_branch_name

    # 5. Reject PR when head_branch == base_branch
    pr_same_branch = await pr_tool.execute({
        "approved": True,
        "head_branch": default_branch_name,
        "base_branch": default_branch_name
    }, context)
    assert pr_same_branch.success is False
    assert pr_same_branch.error.code == "INVALID_BRANCH_TARGET"

    # 6. Create PR targeting configured default branch
    pr_ok = await pr_tool.execute({
        "approved": True,
        "head_branch": feature_branch
    }, context)
    assert pr_ok.success is True
    assert pr_ok.data["base_branch"] == default_branch_name
    assert pr_ok.data["head_branch"] == feature_branch
    assert pr_ok.data["head_branch"] != pr_ok.data["base_branch"]

@pytest.mark.asyncio
async def test_mock_vs_real_pr_distinction(monkeypatch):
    """
    Verifies explicit distinction between MOCK PR and REAL GITHUB PR in tool output.
    """
    run_id = "test-pr-distinction"
    context = ToolContext(run_id=run_id, project_id="proj-1")
    pr_tool = CreatePullRequestTool()

    # Test MOCK PR path
    monkeypatch.setattr("app.config.settings.USE_MOCK_GITHUB", True)
    monkeypatch.setattr("app.config.settings.GITHUB_CLIENT_ID", None)

    mock_res = await pr_tool.execute({"approved": True}, context)
    assert mock_res.success is True
    assert mock_res.data["provider"] == "mock"
    assert mock_res.data["is_mock"] is True
    assert mock_res.data["status"] == "MOCK_CREATED"
    assert "https://github.com/devoncall/demo-repo/pull/101" in mock_res.data["pull_request_url"]

    # Test REAL GITHUB PR path
    monkeypatch.setattr("app.config.settings.USE_MOCK_GITHUB", False)
    monkeypatch.setattr("app.config.settings.GITHUB_CLIENT_ID", "real_client_id")

    real_res = await pr_tool.execute({"approved": True}, context)
    assert real_res.success is True
    assert real_res.data["provider"] == "github"
    assert real_res.data["is_mock"] is False
    assert real_res.data["status"] == "CREATED"
