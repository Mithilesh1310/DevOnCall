import os
import shutil
import logging
from typing import Set, Tuple, Optional, List
from fastapi import HTTPException, status

logger = logging.getLogger("devoncall.workspace.manager")

PROTECTED_FILE_PATTERNS: Set[str] = {
    ".git", ".env", ".env.local", ".env.development", ".env.production", ".env.test",
    "id_rsa", "id_rsa.pub", "id_ed25519", "credentials", "shadow", "master.key"
}

MAX_FILES_CHANGED = 20
MAX_FILE_SIZE_BYTES = 1024 * 1024  # 1MB

class WorkspaceManager:
    """
    Manages isolated per-run workspace environments, path sandboxing, and file guardrails.
    Guarantees file operations remain strictly contained within workspaces/<run_id>/repository/.
    """

    def __init__(self, base_workspaces_dir: str | None = None):
        if base_workspaces_dir is None:
            # Default root workspaces directory in project root
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            self.base_workspaces_dir = os.path.join(root_dir, "workspaces")
        else:
            self.base_workspaces_dir = base_workspaces_dir

    @classmethod
    def get_workspace_path(cls, workspace_id: str) -> str:
        ws_root = default_workspace_manager.get_workspace_root(workspace_id)
        os.makedirs(ws_root, exist_ok=True)
        return ws_root

    def get_workspace_root(self, run_id: str) -> str:
        return os.path.join(self.base_workspaces_dir, run_id, "repository")

    def create_workspace(self, run_id: str, default_branch: str = "main") -> Tuple[str, str, str]:
        """
        Creates an isolated workspace directory and returns (workspace_path, branch_name, base_commit_sha).
        """
        ws_root = self.get_workspace_root(run_id)
        os.makedirs(ws_root, exist_ok=True)

        branch_name = f"devoncall/agent/{run_id[:8]}"
        base_commit_sha = "a1b2c3d4e5f67890"

        logger.info(f"Created isolated workspace for run '{run_id}' at '{ws_root}' (Branch: '{branch_name}')")
        return ws_root, branch_name, base_commit_sha

    def resolve_workspace_path(self, run_id: str, relative_path: str) -> Tuple[bool, str, Optional[str]]:
        """
        Validates and resolves a relative path strictly inside the run's workspace.
        Returns (is_valid, resolved_absolute_path, error_message).
        """
        ws_root = os.path.abspath(self.get_workspace_root(run_id))
        clean_rel = relative_path.strip()

        # 1. Reject absolute paths
        if os.path.isabs(clean_rel) or clean_rel.startswith("/") or clean_rel.startswith("\\"):
            return False, "", f"Absolute paths are forbidden: '{clean_rel}'"

        # 2. Compute absolute target path
        target_abs = os.path.abspath(os.path.join(ws_root, clean_rel))

        # 3. Path Traversal Check (Must start with workspace root)
        if not target_abs.startswith(ws_root):
            return False, "", f"Path traversal rejected: '{relative_path}' escapes workspace boundary"

        # 4. Protected File Checks
        parts = clean_rel.replace("\\", "/").split("/")
        for part in parts:
            part_lower = part.lower()
            if part_lower in PROTECTED_FILE_PATTERNS or part_lower.startswith(".env"):
                return False, "", f"Protected file access denied: '{relative_path}' is protected by security policy"

        # 5. Symlink Escape Verification
        if os.path.islink(target_abs):
            real_target = os.path.realpath(target_abs)
            if not real_target.startswith(ws_root):
                return False, "", f"Symlink escape rejected: '{relative_path}' points outside workspace"

        return True, target_abs, None

    def read_file_safe(self, run_id: str, relative_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> Tuple[bool, dict, Optional[str]]:
        valid, abs_path, err = self.resolve_workspace_path(run_id, relative_path)
        if not valid:
            return False, {}, err

        if not os.path.exists(abs_path):
            return False, {}, f"File '{relative_path}' does not exist in workspace."

        if os.path.isdir(abs_path):
            return False, {}, f"Path '{relative_path}' is a directory, not a file."

        # Check file size limit
        file_size = os.path.getsize(abs_path)
        if file_size > MAX_FILE_SIZE_BYTES:
            return False, {}, f"File '{relative_path}' exceeds maximum size limit (1MB)."

        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            total_lines = len(lines)
            start_idx = (start_line - 1) if start_line and start_line > 0 else 0
            end_idx = end_line if end_line and end_line <= total_lines else total_lines

            selected_lines = lines[start_idx:end_idx]
            content = "".join(selected_lines)

            # Cap returned characters
            truncated = False
            if len(content) > 50000:
                content = content[:50000]
                truncated = True

            return True, {
                "path": relative_path,
                "start_line": start_idx + 1,
                "end_line": min(end_idx, total_lines),
                "total_lines": total_lines,
                "content": content,
                "truncated": truncated
            }, None
        except Exception as e:
            return False, {}, f"Failed to read file '{relative_path}': {str(e)}"

    def write_file_safe(self, run_id: str, relative_path: str, content: str) -> Tuple[bool, dict, Optional[str]]:
        valid, abs_path, err = self.resolve_workspace_path(run_id, relative_path)
        if not valid:
            return False, {}, err

        if len(content.encode("utf-8")) > MAX_FILE_SIZE_BYTES:
            return False, {}, f"File content for '{relative_path}' exceeds maximum size limit (1MB)."

        try:
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            exists_before = os.path.exists(abs_path)
            
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content)

            return True, {
                "path": relative_path,
                "exists_before": exists_before,
                "bytes_written": len(content.encode("utf-8")),
                "lines_count": len(content.splitlines())
            }, None
        except Exception as e:
            return False, {}, f"Failed to write file '{relative_path}': {str(e)}"

default_workspace_manager = WorkspaceManager()
