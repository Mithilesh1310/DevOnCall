# DevOnCall Phase 5 Technical Specification: Isolated Docker Sandbox & Controlled Code Validation

This document outlines the architecture, security policies, resource limits, command allowlists, and execution model for **DevOnCall Phase 5**.

---

## 1. Sandbox Architecture Overview

DevOnCall executes code validation (testing, building, linting, typechecking) inside an isolated sandbox container. Arbitrary shell execution directly on the host is strictly prohibited.

```
Phase 3 Workspace
       │
       ▼
SandboxManager (EXECUTE_SANDBOX permission check)
       │
       ▼
DockerSandboxProvider (or MockSandboxProvider fallback)
       │
       ▼
Container Sandbox (--network none, --cpus 2.0, --memory 1g, mounted workspace)
       │
       ▼
Captured Output (stdout/stderr capped to 2MB) ──► SandboxRun DB Record ──► AgentRuntime / UI
```

---

## 2. Security Boundaries & Permissions Model

- **Permission Required**: `ToolPermission.EXECUTE_SANDBOX`.
- **`PRODUCTION` Permission**: Strictly **DENIED** (`PRODUCTION = "PRODUCTION"`).
- **Network Isolation**: `NETWORK_ENABLED = False` (`--network none`). Containers cannot access arbitrary external APIs or internet resources.
- **Mount Safety**: Only the isolated Phase 3 workspace path (`workspaces/<run_id>/repository/`) is mounted into `/workspace` inside the container. Host root filesystem, Docker socket (`/var/run/docker.sock`), SSH keys, `.env` files, and cloud credentials are **NEVER** mounted.

---

## 3. Command Allowlist Enforcement

Arbitrary shell strings (`POST /execute?command=rm -rf /`) are strictly rejected. Validation runs are requested using structured `CommandType` enums:

| CommandType | Default Python Command | Default Node.js Command |
|---|---|---|
| `TEST` | `pytest` | `npm test` |
| `BUILD` | `python -m build` | `npm run build` |
| `LINT` | `flake8` | `npm run lint` |
| `TYPECHECK` | `mypy .` | `npx tsc --noEmit` |

---

## 4. Resource Limits & Configuration

Resource limits are configurable via environment variables:

- `SANDBOX_CPU_LIMIT`: `2.0` cores
- `SANDBOX_MEMORY_LIMIT`: `1g` (1 GB)
- `SANDBOX_TIMEOUT_SECONDS`: `120` seconds
- `SANDBOX_MAX_OUTPUT_BYTES`: `2097152` bytes (2 MB)

---

## 5. Docker Unavailable & Mock Fallback Strategy

When Docker CLI or daemon is unavailable on the host system:
- `DockerSandboxProvider.run_validation` returns status `BLOCKED` with error message `DOCKER_UNAVAILABLE`.
- `MockSandboxProvider` executes deterministic validation scenarios (`PASS`, `FAIL`, `TIMEOUT`, `ERROR`) for unit testing and offline development.
- UI explicitly badges execution provider: `MOCK SANDBOX` vs `DOCKER SANDBOX`.
