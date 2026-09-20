# DevOnCall Sentry Integration Specification

## Overview

DevOnCall integrates with Sentry as an **Input & Observability Source**. Sentry webhooks are ingested, authenticated, normalized, redacted, deduplicated, and mapped to connected DevOnCall projects.

---

## Security Boundaries & Containment

1. **Input Only**: Sentry integration is strictly read-only and observability-driven. It **NEVER** modifies production, restarts production services, deploys, rolls back, or modifies production databases.
2. **Webhook Verification**: Incoming webhooks on `POST /api/v1/webhooks/sentry` are verified using HMAC SHA256 signatures (`sentry-hook-signature` header). Invalid signatures return `401 Unauthorized`.
3. **Secret Redaction**: Authorization headers, cookies, passwords, tokens, API keys, and sensitive keys are automatically redacted using `SentryNormalizer.redact_dict` before database storage or UI display.
4. **Mock vs Real Distinction**: Simulated or test webhooks are marked as `source: MOCK_SENTRY` and `is_mock: true`. Real webhooks are marked as `source: SENTRY` and `is_mock: false`.

---

## Ingestion Architecture

```
Sentry Event / Webhook
   │
   ▼
POST /api/v1/webhooks/sentry
   │
   ├─► Signature Verification (verify_sentry_signature)
   ├─► Normalization & Redaction (SentryNormalizer.normalize_event)
   ├─► Project Mapping (Sentry project slug ➔ DevOnCall Project)
   ├─► Idempotent Deduplication (external_issue_id / external_event_id)
   └─► Database Persistence (Incident table update/create)
```

---

## API Endpoints

- `POST /api/v1/webhooks/sentry`: Ingest real Sentry webhook.
- `POST /api/v1/webhooks/sentry/simulate`: Trigger mock Sentry webhook simulation.
