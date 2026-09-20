# Production Observability & Incident Intelligence (Phase 11)

DevOnCall Production Observability provides a standardized telemetry ingestion, secret scrubbing, fingerprint deduplication, release correlation, Project Brain integration, and incident intelligence layer.

> **CRITICAL SECURITY GUARANTEE**: Production remains strictly **READ_ONLY**. Production telemetry ingestion, observation lookup, and incident intelligence reports **CANNOT** execute production shell commands, write to production filesystems or databases, restart production services, deploy to production, or perform autonomous production rollbacks.

---

## 1. Provider Architecture (`BaseObservabilityProvider`)

Telemetry is ingested via modular providers defined under `apps/api/app/services/observability/providers/`:

```
                       PRODUCTION OBSERVABILITY ARCHITECTURE
                       
       [Sentry Webhook]        [Generic Webhook]         [Mock Provider]
              │                        │                        │
              ▼                        ▼                        ▼
      ┌──────────────────────────────────────────────────────────────────┐
      │                   Sentry / Generic / Mock Provider               │
      │        (HMAC Signature Verification & Payload Parsing)           │
      └────────────────────────────────┬─────────────────────────────────┘
                                       │
                                       ▼
      ┌──────────────────────────────────────────────────────────────────┐
      │       ObservabilityNormalizer & BrainSecretRedactor             │
      │           (Scubs Passwords, Tokens, API Keys, DSNs)              │
      └────────────────────────────────┬─────────────────────────────────┘
                                       │
                                       ▼
      ┌──────────────────────────────────────────────────────────────────┐
      │         ObservabilityFingerprinter & Deduplicator                │
      │      (SHA-256 Fingerprint: Excludes volatile timestamps)          │
      └────────────────────────────────┬─────────────────────────────────┘
                                       │
                                       ▼
      ┌──────────────────────────────────────────────────────────────────┐
      │                 ProductionReleaseCorrelator                      │
      │   (Correlates Commits, Repo Snapshot, Brain, Staging Deployments)│
      └────────────────────────────────┬─────────────────────────────────┘
                                       │
                                       ▼
      ┌──────────────────────────────────────────────────────────────────┐
      │                   IncidentIntelligenceReport                     │
      │   (Explicitly separates VERIFIED FACTS, CORRELATIONS, HYPOTHESES)│
      └────────────────────────────────┬─────────────────────────────────┘
                                       │
                                       ▼
      ┌──────────────────────────────────────────────────────────────────┐
      │       Handoff to Phase 4 Investigation & Phase 3 Workspace       │
      │      (Isolated Edits ➔ Sandbox ➔ Browser ➔ Staging ➔ Approval)  │
      └──────────────────────────────────────────────────────────────────┘
```

---

## 2. Webhook Ingestion & HMAC Security

Webhooks arrive at `POST /api/v1/observability/webhooks/{provider}`:
- **Sentry Provider**: Verifies HMAC SHA-256 signature header (`sentry-hook-signature`).
- **Generic Provider**: Verifies HMAC SHA-256 signature header (`x-webhook-signature`).
- **Payload Limits**: Rejects payloads exceeding `2MB` with HTTP 413.
- **Invalid Signatures**: Rejects untrusted or spoofed signatures with HTTP 401 UNAUTHORIZED (`SECURITY_POLICY_VIOLATION`).

---

## 3. Fingerprinting & Deduplication

Stable event fingerprinting prevents incident duplication:
- **Fingerprint Formula**: SHA-256 hash of `provider:event_type:service:message:stack_frame:endpoint` (timestamps and volatile numbers removed).
- **Deduplication Behavior**:
  - Increments `occurrence_count`.
  - Updates `last_seen_at`.
  - Reopens status to `OPEN` if previously `RESOLVED`.
  - Preserves original `first_seen_at`.
  - Does **NOT** create duplicate observation records.

---

## 4. Release & Staging Correlation

`ProductionReleaseCorrelator` correlates production observations with engineering context:
- **Repository Commit Correlation**: Matches telemetry `commit_sha` against repository snapshot tree. If commit is unavailable, marks confidence as `UNKNOWN` (never invents a commit!).
- **Project Brain Context**: Queries relevant monorepo service nodes, database schemas, and previous incident/fix records.
- **Staging Deployment Correlation**: Identifies Phase 9 staging deployments for matching commits and records `"Temporal correlation detected: Observation commit 'abc' matches Staging Deployment #stg-101"`.

---

## 5. Incident Intelligence Report

`IncidentIntelligenceService` formats structured intelligence reports with explicit evidence separation:
1. **VERIFIED FACTS**: Telemetry environment, provider, service, severity, occurrence count, first/last seen timestamps.
2. **CORRELATIONS**: Repo commit matches, Project Brain nodes, historical incidents, temporal staging correlations.
3. **HYPOTHESES**: Suspected root cause hypotheses and affected files.
4. **PROPOSED NEXT STEPS**: Handoff to Phase 4 root-cause investigation, Phase 3 workspace, Phase 5 sandbox, Phase 7 browser verification, and Phase 9 staging deployment.

---

## 6. Production READ_ONLY Safety Boundary

`ProductionSafetyPolicy` enforces strict boundary rules:
- **Allowed Operations**: Ingesting telemetry, inspecting observations, correlating commits, querying Project Brain, initiating Phase 4 root-cause investigation, proposing workspace fixes, running sandbox/browser tests, deploying to staging, requesting human approval.
- **Forbidden Operations**: Production shell execution (`PRODUCTION_SHELL`), production filesystem writes (`PRODUCTION_FS_WRITE`), production database mutations (`PRODUCTION_DB_WRITE`), restarting production services (`PRODUCTION_RESTART`), production deployments (`PRODUCTION_DEPLOY`), or rollbacks (`PRODUCTION_ROLLBACK`).
