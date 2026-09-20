# DevOnCall Automated Incident Intelligence & Root-Cause Investigation

## Overview

The Incident Intelligence layer processes Sentry stack traces, correlates frames with repository snapshots, executes `READ_ONLY` agent investigations, formulates `RootCauseHypothesis` and `ProposedFix` entities, and hands off to Phase 3 workspace coding workflows under human approval gates.

---

## Investigation Flow

```
Incident Record (Sentry)
   │
   ▼
POST /api/v1/incidents/{id}/investigate
   │
   ├─► StackFrameParser (Parse JS/TS & Python frames)
   ├─► RepositoryCorrelator (Match frames against RepositorySnapshot.tree)
   ├─► AgentRuntime Execution (READ_ONLY investigation tools)
   ├─► RootCauseHypothesis (Confidence score, evidence list, suspected files)
   └─► ProposedFix (Fix summary, target files, validation plan, risk level)
   │
   ▼
POST /api/v1/incidents/{id}/propose-fix
   │
   └─► Hand off to Phase 3 AgentRuntime (Workspace modification under Human Approval Gate)
```

---

## Stack Trace Parsing & Correlation

- **JS/TS Parsing**: `at functionName (src/api/users.ts:42:17)`
- **Python Parsing**: `File "app/services/user.py", line 42, in get_user_email`
- **Correlation**: `RepositoryCorrelator` maps stack frames against `RepositorySnapshot.tree`, marking matches as `MATCHED` (confidence `1.0`) or `UNMATCHED` (confidence `0.0`).
