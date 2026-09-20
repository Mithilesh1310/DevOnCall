# Agent Runtime & Controlled Tool System Specification

This document details the architectural design, permission guardrails, tool registry, planner abstractions, and execution loop for **DevOnCall Phase 2**.

---

## 1. Overview & Architecture

DevOnCall Phase 2 turns the platform into a controlled AI-agent execution runtime.

```
USER TASK / API
      │
      ▼
┌────────────────────────────────────────────────────────┐
│ AgentRuntime (Execution Loop)                          │
│ - Manages AgentState                                   │
│ - Enforces MAX_AGENT_ITERATIONS = 10                   │
│ - Controls State Transitions                           │
└─────────┬────────────────────────────────────┬─────────┘
          │                                    │
          ▼                                    ▼
┌──────────────────┐                 ┌──────────────────┐
│ BasePlanner      │                 │ ToolExecutor     │
│ (MockPlanner)    │                 │ - Enforces Policy│
└──────────────────┘                 └─────────┬────────┘
                                               │
                                               ▼
                                     ┌──────────────────┐
                                     │ ToolRegistry     │
                                     │ (READ_ONLY Tools)│
                                     └──────────────────┘
```

---

## 2. Security Boundary & Permission Model

### Permission Levels (`ToolPermission`)
- `READ_ONLY`: Allowed in Phase 2 (`repository_info`, `repository_tree`, `file_metadata`, `search_repository`, `project_snapshot`).
- `WRITE_WORKSPACE`: Disabled in Phase 2.
- `EXECUTE_SANDBOX`: Disabled in Phase 2.
- `PRODUCTION`: Disabled in Phase 2.

### Hard Security Rules:
1. **Strict READ_ONLY Enforcement**: Attempting to execute any tool with permissions higher than `READ_ONLY` immediately returns a structured authorization error.
2. **Registry Protection**: Unknown or unregistered tools (e.g. `shell.execute`, `subprocess.run`) are rejected with `TOOL_NOT_FOUND`.
3. **No Shell or Code Modification**: Zero terminal execution, Python `eval`, or local codebase modification capability.
4. **No Chain-of-Thought Secrets**: No hidden chain-of-thought or prompt secrets are logged or persisted.

---

## 3. Phase 2 Tools Specification

1. **`repository_info`**: Returns repository identity, default branch, latest commit SHA, detected languages, frameworks, and file stats.
2. **`repository_tree`**: Returns normalized tree hierarchy filtered by path or `max_depth`.
3. **`file_metadata`**: Returns file extension, size, and node metadata without downloading raw content.
4. **`search_repository`**: Deterministically searches file paths, names, and manifests matching a query string.
5. **`project_snapshot`**: Returns full structured `RepositorySnapshot` payload.

---

## 4. Planner & Execution Loop

### MockPlanner Sequence:
1. Step 0: `repository_info`
2. Step 1: `repository_tree` (`max_depth: 3`)
3. Step 2: `project_snapshot`
4. Step 3: `complete`

### Loop Guardrails:
- `MAX_AGENT_ITERATIONS = 10`: Hard limit on iterations per run.
- Structured `ToolResult` format:
  ```json
  {
    "success": true,
    "tool": "repository_info",
    "data": { ... },
    "error": null
  }
  ```
