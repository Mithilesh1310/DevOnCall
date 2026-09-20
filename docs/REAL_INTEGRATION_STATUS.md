# DevOnCall V1 — Real Infrastructure Integration & Reality Audit Report

## Overview

This report provides an immutable, transparent audit of DevOnCall's integration status with external services and infrastructure providers across all 10 claimed system integrations.

DevOnCall V1 strictly enforces a **NO SYNTHETIC SUCCESS POLICY**: runtime code NEVER returns fabricated PR URLs, simulated staging deployments, or fake production release confirmations. If credentials or infrastructure are missing, the system truthfully returns `NOT_CONFIGURED` or `BLOCKED`.

---

## Integration Status Table

| Integration | Status | Provider | Real Verification Evidence | Blocker / Setup Instruction |
|---|---|---|---|---|
| **GITHUB** | `NOT_CONFIGURED` | GitHub REST API v3 | Checked `GITHUB_TOKEN` & `GITHUB_PAT`. `GitHubProvider` ready. Token missing from environment; no fake tokens or MockGitHubProvider used in runtime verification. | Configure `GITHUB_TOKEN` or `GITHUB_PAT` in environment to enable real repository inspection, tree fetching, file retrieval, commit lookup, and PR management. |
| **POSTGRESQL** | `REAL` | PostgreSQL 16 (AsyncPG) | Executed `SELECT 1` query on async database engine. All 13 Alembic migrations (0001-0013) applied. | None. Database active and verified. |
| **REDIS** | `REAL` | Redis 7 Server | Executed Redis async client `PING` command and received `PONG`. | None. Redis active and verified. |
| **DOCKER** | `REAL` | Docker Engine Container Runtime | Verified Docker CLI binary at PATH and queried `docker info`. Sandbox and Staging containers build cleanly. | None. Docker daemon active and verified. |
| **PLAYWRIGHT** | `REAL` | Playwright Headless Chromium Engine | Launched headless Chromium browser instance (`browser.version`) and verified context isolation. | None. Playwright Chromium active and verified. |
| **SENTRY** | `NOT_CONFIGURED` | Sentry Observability Platform | Checked `SENTRY_DSN` and `SENTRY_WEBHOOK_SECRET`. Webhook signature validator active. | Configure `SENTRY_DSN` and `SENTRY_WEBHOOK_SECRET` in `.env` to receive live Sentry production incident webhooks. |
| **WHATSAPP** | `NOT_CONFIGURED` | Meta WhatsApp Cloud API v18.0 | Checked `WHATSAPP_PHONE_NUMBER_ID` and `WHATSAPP_ACCESS_TOKEN`. SHA-256 phone hash authorizer active. | Configure `WHATSAPP_PHONE_NUMBER_ID` and `WHATSAPP_ACCESS_TOKEN` in `.env` to receive and send live WhatsApp developer messages. |
| **STAGING_DEPLOYMENT** | `NOT_CONFIGURED` | Cloud Staging Provider (AWS / GCP / Docker) | Checked `STAGING_PROVIDER` and `STAGING_API_TOKEN`. `DockerStagingProvider` ready for local container allocation. | Configure `STAGING_PROVIDER` and `STAGING_API_TOKEN` in `.env` for cloud staging deployment. |
| **OBSERVABILITY** | `NOT_CONFIGURED` | Telemetry Webhook Ingestion Engine | Checked `OBSERVABILITY_WEBHOOK_SECRET` and `SENTRY_WEBHOOK_SECRET`. HMAC SHA-256 signature verification active. | Configure `OBSERVABILITY_WEBHOOK_SECRET` in `.env` to ingest live telemetry signals. |
| **PRODUCTION_DEPLOYMENT** | `NOT_CONFIGURED` | Production Release Provider | Checked `PRODUCTION_DEPLOYMENT_PROVIDER` and `PRODUCTION_DEPLOYMENT_TOKEN`. Double human approval release gate active. | Configure `PRODUCTION_DEPLOYMENT_PROVIDER` and `PRODUCTION_DEPLOYMENT_TOKEN` in `.env` or Server Secret Manager. |

---

## Central Registry API

DevOnCall exposes a central integration status inspection endpoint:

```
GET /api/v1/system/integrations
```

### Sample API Response Payload:
```json
{
  "system_mode": "REAL",
  "total_integrations": 10,
  "summary": {
    "REAL": 4,
    "NOT_CONFIGURED": 6,
    "BLOCKED": 0,
    "ERROR": 0
  },
  "integrations": [
    {
      "name": "GITHUB",
      "provider": "GitHub REST & GraphQL API",
      "status": "NOT_CONFIGURED",
      "health": "Missing GITHUB_TOKEN or GITHUB_APP_ID in environment.",
      "required_environment": ["GITHUB_TOKEN", "GITHUB_REPOSITORY_NAME"],
      "details": { "reason": "No GitHub credentials configured." },
      "last_verified_at": "2026-09-20T16:56:50+00:00"
    },
    {
      "name": "POSTGRESQL",
      "provider": "PostgreSQL 16 (AsyncPG)",
      "status": "REAL",
      "health": "PostgreSQL database connected and responsive.",
      "required_environment": ["DATABASE_URL"],
      "details": { "dialect": "postgresql+asyncpg", "connection_status": "ACTIVE" },
      "last_verified_at": "2026-09-20T16:56:50+00:00"
    }
  ],
  "evaluated_at": "2026-09-20T16:56:50+00:00"
}
```

---

## Security & Runtime Policy Guarantees

1. **`TEST_MODE` Isolation**:
   Mock providers are restricted strictly to unit test files (`apps/api/tests/`) or runtime executions where `TEST_MODE=true` is explicitly passed.
2. **No Arbitrary Shell Execution**:
   Command executions pass through explicit argument vectors (`asyncio.create_subprocess_exec("docker", ...)`). `shell=True` and `eval()` are forbidden.
3. **Secret Redaction**:
   All API payloads, logs, Project Brain nodes, and WhatsApp responses scrub API keys, tokens, and passwords using `BrainSecretRedactor`.
4. **Credential Isolation**:
   Production release tokens reside strictly inside server secret managers and are NEVER passed to the LLM agent runtime or Project Brain.
