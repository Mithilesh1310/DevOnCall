# DevOnCall Architecture & Technical Blueprint

This document outlines the architectural design, system boundaries, data flow, and extension points for **DevOnCall**.

---

## 1. System Overview

DevOnCall is designed as an autonomous AI Production Software Engineer platform. Its fundamental mission is to handle production incidents end-to-end:

```
```
```
Sentry Event / Webhook (Observability Input)
         │
         ▼
[ SentryNormalizer & Redaction ] ───► [ Project Correlation & Deduplication ]
         │
         ▼
[ IncidentInvestigator ] ───► Correlate Stack Frames ───► RootCauseHypothesis & ProposedFix
         │
         ▼
[ Phase 3 Code Agent Workspace ] ───► Isolated Edits
         │
         ▼
[ Phase 5 Docker Sandbox ] ───► Controlled Validation (TEST/BUILD/LINT)
         │
         ▼
[ Phase 7 Playwright Browser ] ───► Isolated UI Verification (Mock / Playwright)
         │
         ▼
[ Phase 6 Automated Verification ] ───► ValidationAnalyzer ───► FailureClassifier ───► RepairPolicy
         │                                                            │
         ├─── (Failure Detected & Retries < 2) ───► Bounded Repair ───┘
         │
         ▼
[ Final Validation PASSED ] ───► Human Approval Gate ───► Pull Request
```

---

## 2. Core Components

### 2.1 Frontend (`apps/web`)
- **Technology**: Next.js 14 (App Router), TypeScript, Tailwind CSS, Lucide Icons.
- **Role**: Provides developers with live visibility into Sentry incidents, stack traces, correlator matches, automated root cause hypotheses, proposed fixes, workspace diffs, sandbox validation controls, Phase 7 Playwright browser verification controls, scenario execution steppers, screenshot previews, console/network error logs, and PR approval gates.

### 2.2 Backend API (`apps/api`)
- **Technology**: Python 3.11+, FastAPI, Pydantic v2, Uvicorn.
- **Architecture**: Versioned REST API (`/api/v1/`), decoupled business logic, and strict dependency injection.
- **Modularity**: Webhook processing (`/api/v1/webhooks/sentry`), incident management (`/api/v1/incidents`), agent execution (`/api/v1/agent/runs`), sandbox runs (`/api/v1/sandbox/runs`), browser verification (`/api/v1/browser/runs`), and validation analyzer/repair policy (`/api/v1/agent/runs/{id}/validation`) are isolated in dedicated modules.

### 2.3 Database Layer (`PostgreSQL`)
- **Technology**: PostgreSQL 16, SQLAlchemy 2.0 (Async), Alembic migrations.
- **Schema**:
  - `Project`: Connected codebases and default branch settings.
  - `Incident`: Production incident records, external Sentry issue IDs, occurrence counts, and stack traces.
  - `IncidentInvestigation`: Investigation status, confidence score, hypotheses, evidence, repository matches, and proposed fixes.
  - `AgentRun`: Agent execution runs, workspace paths, feature branches, diff summaries, and PR metadata.
  - `SandboxRun`: Isolated code validation run metadata, command types, stdout/stderr logs, duration, and status.
  - `ValidationAttempt`: Iteration tracking, command types, failure classification, diagnostic payload, and repair decisions.
  - `BrowserRun` & `BrowserStepResultModel`: Browser UI verification scenario runs, step results, screenshots, console errors, and failed network logs.

---

## 3. Phase 7 Playwright Browser Verification Architecture

- **`BrowserManager` & Providers (`apps/api/app/services/browser/`)**:
  - Requires `BROWSER_SANDBOX` permission. `PRODUCTION` permission remains **DENIED**.
  - Dual Provider Architecture: `MockBrowserProvider` for deterministic offline verification & unit testing; `PlaywrightBrowserProvider` for real headless Chromium execution with fresh context isolation (`new_context()`).
  - Strict URL allowlisting (`BROWSER_ALLOWED_BASE_URLS`, default `http://localhost:3000`).
  - Security Enforcements: Blocks `file://`, `chrome://`, `169.254.169.254`, metadata endpoints, and internal infrastructure ports (22, 5432, 6379).
  - Credential Redaction (`CredentialRedactor`): Secret tokens, passwords, cookies, and auth headers are automatically scrubbed from outputs, logs, and screenshots.
  - Artifact Management (`BrowserArtifactManager`): Enforces `MAX_SCREENSHOT_SIZE_MB = 5` and path traversal bounds.
  - `BrowserFailureClassifier`: Classifies browser failures (`ELEMENT_NOT_FOUND`, `ASSERTION_FAILED`, `NETWORK_ERROR`, `CONSOLE_ERROR`, `APPLICATION_NOT_READY`) and maps network 500s or console errors to repository files.

---

## 5. Phase 8 WhatsApp Developer Interface Architecture

- **`WhatsAppManager` & Integration Boundary (`apps/api/app/services/integrations/whatsapp/`)**:
  - Official Meta Cloud API Boundary (`WhatsAppCloudClient`): Communicates with official Meta Graph API (`/v18.0/{phone_number_id}/messages`).
  - Offline Simulation Provider (`MockWhatsAppProvider`): For deterministic offline verification and unit testing.
  - No Web Scraping / QR Automation: Strictly avoids unauthorized WhatsApp Web scraping or browser control.
  - Security & Authorization Matrix (`WhatsAppSecurityPolicy`):
    - Sender phone numbers are hashed with HMAC SHA256 before verification.
    - Role-based permissions (`VIEWER`, `DEVELOPER`, `APPROVER`, `ADMIN`).
    - Single-Use Confirmation Tokens (`ConfirmationToken`): High-impact commands (`FIX`, `APPROVE`, `REJECT`) generate a 6-character short-lived token expiring in 10 minutes.
    - Prompt Injection Neutralization: Cleans incoming raw text against malicious injection payloads.
    - Secret Redaction (`WhatsAppResponseRedactor`): Scrubs API keys, GitHub tokens, and JWTs from outgoing responses.
    - Production Permission Denied: Production deployments remain strictly denied; PR creation requires explicit human approval.

---

## 6. Phase 9 Staging Deployment + Autonomous Verification Gate Architecture

- **`StagingManager` & Providers (`apps/api/app/services/staging/`)**:
  - Permission: Introduced `STAGING_DEPLOY` permission. `PRODUCTION` permission remains **STRICTLY DENIED**.
  - Dual Provider Architecture: `MockStagingProvider` for deterministic offline verification & scenarios; `DockerStagingProvider` for real container execution inside isolated `staging-net-<id>` networks.
  - Absolute Production Boundary (`StagingSecurityPolicy`): Rejects any API parameter or command specifying `environment: "production"` with HTTP 403 / `SECURITY_POLICY_VIOLATION`.
  - Verification Stages: Reuses Phase 5 Sandbox for BUILD stage, executes `StagingHealthChecker` (polling `/health` endpoint), `StagingSmokeTester` (allowlisted GET probes), and reuses Phase 7 `BrowserManager` targeted at allocated staging URLs.
  - Resource Cleanup (`StagingCleanupManager`): Automatic container, network, and volume teardown on failure or retention expiration (`STAGING_RETENTION_MINUTES=60`).

---

## 7. Phase 10 Project Brain Architecture

- **`BrainManager` & Knowledge Layer (`apps/api/app/services/brain/`)**:
  - Persistent, queryable engineering memory stored in PostgreSQL (`ProjectBrainNodeModel`, `ProjectBrainEdgeModel`, `ProjectBrainEventModel`).
  - **Deterministic Repository Scan**: `RepositoryBrainExtractor` consumes Phase 1 snapshots to build nodes for monorepo project roots, services (`apps/api`, `apps/web`), database schemas, and relationships.
  - **Node Deduplication**: Keys (e.g. `service:apps/api`, `database:alembic_postgres`) prevent duplicates across repeated repository scans while logging a `FACT_UPDATED` event in the audit ledger.
  - **Strict Provenance & Confidence**: Distinguishes `VERIFIED` facts (repository scan / human explicitly) from `HIGH`/`MEDIUM`/`LOW` pipeline evidence.
  - **Secret Redaction (`BrainSecretRedactor`)**: Scrubs credentials, API tokens, DSNs, and secret keys before persistence and output.
  - **Agent Tool (`project_brain_query`)**: Registered as `READ_ONLY` in `ToolRegistry` for safe context retrieval by agent runs.
  - **WhatsApp Commands (`BRAIN`)**: Enables developers to query engineering memory, summary metrics, and incident history directly from mobile.

---

## 8. Phase 11 Production Observability & Incident Intelligence Architecture

- **Observability Provider Architecture (`apps/api/app/services/observability/`)**:
  - `BaseObservabilityProvider` interface with `MockObservabilityProvider`, `SentryObservabilityProvider`, and `GenericWebhookProvider`.
  - **Webhook Security**: HMAC SHA-256 signature verification (`sentry-hook-signature`, `x-webhook-signature`), secret scrubbing (`BrainSecretRedactor`), payload size limits (2MB max), and 401/403 rejection.
  - **Fingerprint Deduplication (`ObservabilityFingerprinter`)**: SHA-256 fingerprinting excluding timestamps. Deduplication increments `occurrence_count` and updates `last_seen_at` without duplicating records.
  - **Production Safety Policy (`ProductionSafetyPolicy`)**: Hard-rejects forbidden actions (`PRODUCTION_SHELL`, `PRODUCTION_FS_WRITE`, `PRODUCTION_DB_WRITE`, `PRODUCTION_RESTART`, `PRODUCTION_DEPLOY`, `PRODUCTION_ROLLBACK`) with `SECURITY_POLICY_VIOLATION`.
  - **Release & Brain Correlation (`ProductionReleaseCorrelator`)**: Correlates observations with repo commits (never inventing commits), Project Brain context, historical incidents, and Phase 9 staging deployment records ("Temporal correlation detected").
  - **Incident Intelligence Report (`IncidentIntelligenceService`)**: Generates reports explicitly separating **VERIFIED FACTS**, **CORRELATIONS**, and **HYPOTHESES**.
  - **Phase 4 Handoff**: Connects production observations to existing Phase 4 investigation pipeline, Phase 3 workspace, Phase 5 sandbox, Phase 7 browser verification, and Phase 9 staging.

---

## 10. Phase 12 Controlled Canary Deployment & Production Safety Gate Architecture

- **`DeploymentManager` & Providers (`apps/api/app/services/deployment/`)**:
  - **Controlled State Machine**: Manages approval-gated lifecycle (`CREATED` → `STAGING_PASSED` → `AWAITING_APPROVAL` → `APPROVED` → `CANARY_DEPLOYED` → `CANARY_VERIFIED` → `APPROVED` → `DEPLOYED` / `ROLLED_BACK`).
  - **Double Human Approval Gates**: Gate 1 for 1-10% Canary Release approval; Gate 2 for Full Production Release approval following Canary Decision Engine PASS.
  - **Canary Traffic Bounds**: Bounded strictly between **1.0%** and **10.0%**.
  - **Canary Decision Engine (`CanaryDecisionEngine`)**: Evaluates real-time telemetry against baseline error rates (+0.5% max diff), latency p95 (+20% max diff), and latency p99 (+25% max diff). Rejects `INSUFFICIENT_DATA` from converting to `PASS`.
  - **Rollback Service (`RollbackService`)**: Immediate, approval-supported automated or manual rollbacks requiring exact 40-character target commit SHAs.
  - **Provider Abstraction (`BaseDeploymentProvider`)**: `MockDeploymentProvider` for test scenarios; `ProductionProvider` for real environment release APIs without shell execution.
  - **LLM Read-Only Boundary**: Agent tools (`release_candidate_status`, `canary_verification_details`, `deployment_audit_log`) strictly enforced with `ToolPermission.READ_ONLY`.

---

## 11. Architectural Safety & Control Rules

1. **Sentry & Observability is Telemetry Only**: Production telemetry integration does **NOT** modify production environments, restart production services, deploy, rollback, or execute production commands.
2. **Sandbox & Browser Network Isolation**: Containers and browser contexts execute with network restrictions limited strictly to allowlisted application base URLs.
3. **No Arbitrary Command Strings or JS**: API and tools reject raw command strings and arbitrary `eval()` / JS injections.
4. **No Direct Default Branch Modifications**: Code edits are committed strictly on `devoncall/agent/<short-run-id>` feature branches.
5. **Human Approval Gate**: PR creation requires explicit human review and approval.
6. **Bounded Execution**: Self-correction is hard-capped (10 iterations max, 5 browser runs max) and halts on repeated failures.
7. **WhatsApp Authorization Required**: Receiving a WhatsApp message is not proof of identity; developer identity must match an authorized database hash with adequate role permissions.
8. **Staging Isolation & Production Denied**: Staging environments execute inside isolated networks with dedicated staging secrets; production parameters are hard rejected.
9. **Project Brain & Observability Read-Only Querying**: Agents and external interfaces access Project Brain and production telemetry via read-only tools and endpoints; secrets are scrubbed prior to persistence.
10. **Double Human Approval Release Gate**: Production releases occur strictly through the Phase 12 state machine; direct LLM production write permission is strictly DENIED.




