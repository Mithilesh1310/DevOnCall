# DevOnCall — Phase 9 Documentation
## Staging Deployment + Autonomous Verification Gate Architecture & Specification

### 1. Overview
DevOnCall Phase 9 introduces isolated Staging Deployment and Autonomous Verification Gates. Once a code fix passes local sandbox and Playwright browser validation and a Pull Request exists, DevOnCall can deploy the exact branch/commit to an isolated STAGING environment, run automated health checks, smoke probes, Playwright browser scenarios, evaluate a staging verdict, and present the result for human review.

---

### 2. Absolute Production Security Boundary
- **`PRODUCTION = DENIED`**: Hard enforcement across all services.
- **Environment Parameter Rejection**: API calls or commands specifying `environment: "production"` are immediately rejected with HTTP `403 FORBIDDEN` / `SECURITY_POLICY_VIOLATION`.
- **Permission Matrix**: Introduced `STAGING_DEPLOY` permission. `PRODUCTION` permission remains **STRICTLY DENIED**.
- **No Production Operations**: Phase 9 strictly prohibits production deployments, rollbacks, DB mutations, shell access, K8s credentials, or canary shifting.

---

### 3. Provider Architecture
- **`BaseStagingProvider`**: Abstract interface defining contracts for `deploy_staging()`, `health_check()`, `teardown_staging()`.
- **`MockStagingProvider`**: Deterministic offline simulation provider supporting scenarios (`PASS`, `BUILD_FAIL`, `DEPLOY_FAIL`, `HEALTH_FAIL`, `SMOKE_FAIL`, `BROWSER_FAIL`, `CANCELLED`).
- **`DockerStagingProvider`**: Real Docker deployment provider creating isolated `staging-net-<id>` networks and containers.
- **Docker Engine Runtime Check**: If Docker engine is not active or accessible, `DockerStagingProvider` reports `is_available = False` and returns `STAGING DOCKER RUNTIME = BLOCKED`.

---

### 4. Staging Isolation & Security Controls
- **Isolated Networks**: Staging containers execute inside dedicated Docker networks (`staging-net-<id>`).
- **Secret Isolation**: Staging uses dedicated staging variables (`DATABASE_URL_STAGING`, `REDIS_URL_STAGING`). Production credentials or secrets are strictly forbidden in staging environments.
- **Container Mounting Restrictions**: Docker mounts for `/var/run/docker.sock`, host filesystem root, SSH keys, or cloud credentials are hard blocked.

---

### 5. Verification Lifecycle & State Machine

```
QUEUED ➔ BUILDING ➔ DEPLOYING ➔ HEALTH_CHECKING ➔ VERIFYING ➔ PASSED / FAILED / BLOCKED
```

1. **BUILD**: Reuses Phase 5 sandbox infrastructure to verify clean compilation.
2. **DEPLOYMENT**: Allocates isolated port and deploys container.
3. **HEALTH CHECK**: `StagingHealthChecker` polls `/health` endpoint until HTTP 200 OK or `STAGING_HEALTH_TIMEOUT_SECONDS=60`.
4. **SMOKE TEST**: `StagingSmokeTester` executes GET probes against allowlisted endpoints (`/`, `/health`, `/api/health`).
5. **PLAYWRIGHT BROWSER VERIFICATION**: Reuses Phase 7 `BrowserManager` targeted at the generated staging URL.
6. **STAGING VERDICT**: Evaluates final status (`PASSED` vs `FAILED`).

---

### 6. Resource Cleanup & Retention
- `StagingCleanupManager`: Automatically tears down containers, networks, and volumes upon failure or retention expiry (`STAGING_RETENTION_MINUTES=60`).
- Prevents orphaned Docker resources.

---

### 7. API Endpoints

- `POST /api/v1/staging/deployments`: Trigger staging deployment (validates `environment: "STAGING"`, rejects `"production"` with 403).
- `GET /api/v1/staging/deployments`: List staging deployments.
- `GET /api/v1/staging/deployments/{id}`: Get staging deployment details.
- `GET /api/v1/staging/deployments/{id}/checks`: Get staging check breakdown.
- `POST /api/v1/staging/deployments/{id}/cancel`: Cancel deployment & cleanup resources.
- `POST /api/v1/staging/deployments/{id}/cleanup`: Manually trigger resource cleanup.
