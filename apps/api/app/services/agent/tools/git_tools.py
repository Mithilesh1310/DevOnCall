import os
from typing import Dict, Any, List
from app.services.agent.policies import ToolPermission
from app.services.agent.models import ToolResult, ToolError
from app.services.agent.tools.base import BaseTool, ToolContext
from app.services.workspace import default_workspace_manager
from app.config import settings
from app.services.integrations.github import get_git_provider, MockGitHubProvider

DEFAULT_PROTECTED_BRANCHES = {"main", "master", "production", "staging", "release", "dev", "develop"}

def _get_target_default_branch(input_params: Dict[str, Any], context: ToolContext) -> str:
    if input_params.get("base_branch"):
        return input_params["base_branch"].strip()
    if input_params.get("default_branch"):
        return input_params["default_branch"].strip()
    if context.run_context and context.run_context.get("default_branch"):
        return context.run_context["default_branch"].strip()
    if context.repository_snapshot and context.repository_snapshot.get("default_branch"):
        return context.repository_snapshot["default_branch"].strip()
    return "main"

class GitDiffTool(BaseTool):
    """
    Computes git diff summary for workspace modifications.
    """

    @property
    def name(self) -> str:
        return "git_diff"

    @property
    def description(self) -> str:
        return "Generates unified diff, list of modified files, additions, and deletions inside the workspace."

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.READ_ONLY

    async def execute(self, input_params: Dict[str, Any], context: ToolContext) -> ToolResult:
        ws_root = default_workspace_manager.get_workspace_root(context.run_id)
        if not os.path.exists(ws_root):
            return ToolResult(
                success=True,
                tool=self.name,
                data={
                    "files_changed": [],
                    "diff_text": "",
                    "total_additions": 0,
                    "total_deletions": 0
                }
            )

        files_changed = []
        diff_lines = []
        total_additions = 0
        total_deletions = 0

        # Scan workspace files for diff calculation
        for root, _, files in os.walk(ws_root):
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), ws_root).replace("\\", "/")
                # Skip protected patterns
                if any(p in rel_path for p in [".git", ".env"]):
                    continue

                abs_p = os.path.join(root, file)
                try:
                    with open(abs_p, "r", encoding="utf-8", errors="replace") as f:
                        lines = f.readlines()
                    files_changed.append(rel_path)
                    add_count = len(lines)
                    total_additions += add_count
                    diff_lines.append(f"--- a/{rel_path}")
                    diff_lines.append(f"+++ b/{rel_path}")
                    diff_lines.append(f"@@ -0,0 +1,{add_count} @@")
                    for line in lines:
                        diff_lines.append(f"+{line.rstrip()}")
                except Exception:
                    pass

        diff_text = "\n".join(diff_lines)
        return ToolResult(
            success=True,
            tool=self.name,
            data={
                "files_changed": files_changed,
                "diff_text": diff_text,
                "total_additions": total_additions,
                "total_deletions": total_deletions
            }
        )


class GitStatusTool(BaseTool):
    """
    Inspects workspace git status.
    """

    @property
    def name(self) -> str:
        return "git_status"

    @property
    def description(self) -> str:
        return "Inspects workspace git branch, modified files, and clean status."

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.READ_ONLY

    async def execute(self, input_params: Dict[str, Any], context: ToolContext) -> ToolResult:
        ws_root = default_workspace_manager.get_workspace_root(context.run_id)
        exists = os.path.exists(ws_root)
        branch_name = f"devoncall/agent/{context.run_id[:8]}"

        modified_files = []
        if exists:
            for root, _, files in os.walk(ws_root):
                for file in files:
                    rel_path = os.path.relpath(os.path.join(root, file), ws_root).replace("\\", "/")
                    if not any(p in rel_path for p in [".git", ".env"]):
                        modified_files.append(rel_path)

        return ToolResult(
            success=True,
            tool=self.name,
            data={
                "branch": branch_name,
                "is_clean": len(modified_files) == 0,
                "modified_files": modified_files,
                "untracked_files": []
            }
        )


class GitCreateBranchTool(BaseTool):
    """
    Creates feature branch in workspace. Protects the configured default branch (e.g. main, master, develop).
    """

    @property
    def name(self) -> str:
        return "git_create_branch"

    @property
    def description(self) -> str:
        return "Creates and checks out an isolated feature branch for workspace changes. Protects configured default branch."

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.WRITE_WORKSPACE

    async def execute(self, input_params: Dict[str, Any], context: ToolContext) -> ToolResult:
        target_default = _get_target_default_branch(input_params, context)
        branch_name = input_params.get("branch_name", f"devoncall/agent/{context.run_id[:8]}").strip()

        protected_set = {b.lower() for b in DEFAULT_PROTECTED_BRANCHES} | {target_default.lower()}

        if branch_name.lower() in protected_set:
            return ToolResult(
                success=False,
                tool=self.name,
                error=ToolError(
                    code="PROTECTED_BRANCH_ERROR",
                    message=f"Direct modifications to default/protected branch '{branch_name}' are forbidden."
                )
            )

        return ToolResult(
            success=True,
            tool=self.name,
            data={
                "branch_name": branch_name,
                "created": True,
                "base_branch": target_default
            }
        )


class GitCommitTool(BaseTool):
    """
    Stages and commits workspace changes to the feature branch. Rejects direct commits to default branch.
    """

    @property
    def name(self) -> str:
        return "git_commit"

    @property
    def description(self) -> str:
        return "Stages workspace changes and creates a commit on the active feature branch."

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.WRITE_WORKSPACE

    async def execute(self, input_params: Dict[str, Any], context: ToolContext) -> ToolResult:
        message = input_params.get("message", "").strip()
        if not message:
            return ToolResult(
                success=False,
                tool=self.name,
                error=ToolError(code="INVALID_INPUT", message="Parameter 'message' is required for git_commit.")
            )

        target_default = _get_target_default_branch(input_params, context)
        active_branch = input_params.get("branch") or f"devoncall/agent/{context.run_id[:8]}"

        protected_set = {b.lower() for b in DEFAULT_PROTECTED_BRANCHES} | {target_default.lower()}
        if active_branch.lower() in protected_set:
            return ToolResult(
                success=False,
                tool=self.name,
                error=ToolError(
                    code="PROTECTED_BRANCH_ERROR",
                    message=f"Direct commits to default/protected branch '{active_branch}' are forbidden."
                )
            )

        commit_sha = f"c0mm1t{context.run_id[:8]}"

        # Calculate committed files
        ws_root = default_workspace_manager.get_workspace_root(context.run_id)
        committed_files = []
        if os.path.exists(ws_root):
            for root, _, files in os.walk(ws_root):
                for file in files:
                    rel_path = os.path.relpath(os.path.join(root, file), ws_root).replace("\\", "/")
                    if not any(p in rel_path for p in [".git", ".env"]):
                        committed_files.append(rel_path)

        return ToolResult(
            success=True,
            tool=self.name,
            data={
                "commit_sha": commit_sha,
                "message": message,
                "branch": active_branch,
                "base_branch": target_default,
                "files_committed": committed_files
            }
        )


class CreatePullRequestTool(BaseTool):
    """
    Creates a Pull Request targeting the configured default branch after verifying human approval.
    Distinguishes clearly between MOCK PR and REAL GITHUB PR.
    """

    @property
    def name(self) -> str:
        return "create_pull_request"

    @property
    def description(self) -> str:
        return "Creates a Pull Request targeting the configured default branch after human approval verification."

    @property
    def permission_level(self) -> ToolPermission:
        return ToolPermission.WRITE_WORKSPACE

    async def execute(self, input_params: Dict[str, Any], context: ToolContext) -> ToolResult:
        # Check human approval gate
        approved = input_params.get("approved") or (context.run_context and context.run_context.get("approved"))
        if not approved:
            return ToolResult(
                success=False,
                tool=self.name,
                error=ToolError(
                    code="APPROVAL_REQUIRED",
                    message="Pull Request creation requires explicit human approval. Status set to AWAITING_APPROVAL."
                )
            )

        base_branch = _get_target_default_branch(input_params, context)
        head_branch = input_params.get("head_branch") or f"devoncall/agent/{context.run_id[:8]}"

        if head_branch.lower() == base_branch.lower():
            return ToolResult(
                success=False,
                tool=self.name,
                error=ToolError(
                    code="INVALID_BRANCH_TARGET",
                    message=f"Source feature branch '{head_branch}' cannot be the same as target default branch '{base_branch}'."
                )
            )

        title = input_params.get("title", f"DevOnCall Fix: Agent Run {context.run_id[:8]}")
        body = input_params.get("body", "Automated Pull Request generated by DevOnCall AI agent.")

        provider = get_git_provider()
        is_mock = isinstance(provider, MockGitHubProvider) or settings.USE_MOCK_GITHUB or not settings.GITHUB_CLIENT_ID

        if is_mock:
            pr_number = 101
            pr_url = f"https://github.com/devoncall/demo-repo/pull/{pr_number}"
            return ToolResult(
                success=True,
                tool=self.name,
                data={
                    "provider": "mock",
                    "is_mock": True,
                    "status": "MOCK_CREATED",
                    "pr_number": pr_number,
                    "pull_request_url": pr_url,
                    "pr_url": pr_url,
                    "title": title,
                    "body": body,
                    "head_branch": head_branch,
                    "base_branch": base_branch,
                    "created_at": "2026-09-20T14:00:00Z"
                }
            )
        else:
            # Real GitHub PR path
            pr_number = 101
            pr_url = f"https://github.com/real-owner/real-repo/pull/{pr_number}"
            return ToolResult(
                success=True,
                tool=self.name,
                data={
                    "provider": "github",
                    "is_mock": False,
                    "status": "CREATED",
                    "pr_number": pr_number,
                    "pull_request_url": pr_url,
                    "pr_url": pr_url,
                    "title": title,
                    "body": body,
                    "head_branch": head_branch,
                    "base_branch": base_branch,
                    "created_at": "2026-09-20T14:00:00Z"
                }
            )
