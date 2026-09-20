# DevOnCall Phase 3 — Code Agent Technical Specification

## Overview

Phase 3 transforms **DevOnCall** from a read-only repository intelligence system into a controlled coding agent capable of investigating code, making workspace modifications in an isolated feature branch, generating diffs, validating changes, and submitting Pull Requests gated by human approval.

---

## 1. System Architecture

```
User Task ("Fix greeting function")
   │
   ▼
DevOnCall Code Agent Runtime
   │
   ├─► 1. Code Investigation (RepositoryInfo, SearchRepository, ReadFile)
   ├─► 2. Workspace Management (WorkspaceManager -> workspaces/<run_id>/repository/)
   ├─► 3. Controlled Modification (WriteFile, ApplyPatch)
   ├─► 4. Diff & Git Commit (GitDiff, GitCommit on devoncall/agent/<short_id>)
   ├─► 5. Human Approval Gate (Status: AWAITING_APPROVAL)
   └─► 6. Pull Request Creation (CreatePullRequest -> PR #101 on main branch)
```

---

## 2. Key Guardrails & Security Policies

1. **No Direct Default Branch Edits**:
   - Modifications always occur inside `devoncall/agent/<short-run-id>` feature branch under `workspaces/<run_id>/repository/`.
   - The primary `main` branch remains protected until human approval is granted.

2. **Path Traversal & Protected Files Containment**:
   - `WorkspaceManager.resolve_workspace_path` verifies all relative file operations stay strictly inside `workspaces/<run_id>/repository/`.
   - Rejects `../` traversal, absolute path escape attempts, symlink escapes, and protected credential files (`.env`, `.env.*`, `.git/`, `id_rsa`, etc.).

3. **No Unrestricted Arbitrary Shell Execution**:
   - Execution remains bounded by registered, policy-enforced Python tools. Arbitrary shell endpoints are strictly forbidden.

4. **Human Approval Gate**:
   - Creating a Pull Request requires explicit human approval via `POST /api/v1/agent/runs/{id}/approve`.
   - Until approved, run status is paused in `AWAITING_APPROVAL`.

---

## 3. Tool Permissions Overview

| Tool Name | Permission Level | Description |
|---|---|---|
| `repository_info` | `READ_ONLY` | Fetches repository metadata & languages |
| `repository_tree` | `READ_ONLY` | Inspects directory hierarchy |
| `project_snapshot` | `READ_ONLY` | Returns structural snapshot |
| `search_repository` | `READ_ONLY` | Searches file paths and file text content |
| `read_file` | `READ_ONLY` | Safe file reader with line range limits |
| `create_workspace` | `WRITE_WORKSPACE` | Initializes per-run workspace & feature branch |
| `write_file` | `WRITE_WORKSPACE` | Writes text safely inside workspace sandbox |
| `apply_patch` | `WRITE_WORKSPACE` | Applies structured unified patch to target file |
| `git_diff` | `READ_ONLY` | Generates unified diff & line statistics |
| `git_status` | `READ_ONLY` | Inspects branch and workspace file status |
| `git_create_branch` | `WRITE_WORKSPACE` | Creates feature branch in workspace |
| `git_commit` | `WRITE_WORKSPACE` | Stages and commits workspace edits |
| `create_pull_request` | `WRITE_WORKSPACE` | Submits PR after human approval verification |

---

## 4. API Specification

### `GET /api/v1/agent/runs/{run_id}/diff`
Returns unified git diff summary:
```json
{
  "files_changed": ["hello.py"],
  "diff_text": "--- a/hello.py\n+++ b/hello.py\n@@ -0,0 +1,3 @@\n+# DevOnCall Agent Fix\ndef hello():\n    return 'Hello DevOnCall!'\n",
  "total_additions": 3,
  "total_deletions": 0
}
```

### `GET /api/v1/agent/runs/{run_id}/changes`
Returns workspace modification state and change plan.

### `POST /api/v1/agent/runs/{run_id}/approve`
Grants human approval and resumes agent execution to create Pull Request:
```json
{
  "run_id": "8a3f9e1b-...",
  "status": "COMPLETED",
  "message": "Agent run approved successfully. Pull Request generated.",
  "pull_request_url": "https://github.com/devoncall/demo-repo/pull/101"
}
```

---

## 5. Verification & Testing

Run unit & integration tests:
```powershell
.\.venv\Scripts\python.exe -m pytest apps/api/tests -v
```

Verify Next.js build:
```powershell
npm run build --prefix apps/web
```
