# DevOnCall Phase 6 — Automated Verification + Agent Feedback + Bounded Self-Correction

This document outlines the architecture, design, failure classification, repair policy, iteration limits, and human review gates introduced in Phase 6 of DevOnCall.

---

## 1. Objective

Phase 6 transforms DevOnCall from a linear:

```
CODE ➔ SANDBOX ➔ RESULT
```

into a controlled, evidence-driven feedback loop:

```
CODE
  ↓
SANDBOX
  ↓
OBSERVE RESULT
  ↓
ANALYZE FAILURE
  ↓
DECIDE NEXT ACTION
  ↓
MODIFY CODE
  ↓
VALIDATE AGAIN
  ↓
PASS / STOP / HUMAN REVIEW
```

---

## 2. Bounded Execution Safeguards & Limits

Self-correction is strictly bounded to prevent infinite loops, execution runaway, and excessive resource consumption.

The following configurable limits are enforced:

| Config Variable | Default Value | Description |
| :--- | :--- | :--- |
| `MAX_AGENT_ITERATIONS` | `10` | Maximum overall iterations per agent run. |
| `MAX_VALIDATION_RUNS` | `10` | Maximum total sandbox validation runs permitted per agent task. |
| `MAX_REPAIR_ATTEMPTS` | `5` | Maximum code modification repair attempts. |
| `MAX_SAME_FAILURE_RETRIES` | `2` | Threshold for consecutive identical failures before halting. |

---

## 3. Failure Classification & Result Normalization

`ValidationAnalyzer` receives raw `SandboxRun` outputs (stdout/stderr) and normalizes them into structured `ValidationResult` objects.

### Statuses
- `PASSED`
- `FAILED`
- `TIMED_OUT`
- `BLOCKED`
- `ERROR`

### Failure Types
- `TEST_FAILURE`: Pytest / Jest test assertion failures.
- `TYPE_ERROR`: TypeScript compiler diagnostics (`TS2532`, `TS2322`, etc.).
- `BUILD_FAILURE`: Webpack / Vite / Build tool compilation errors.
- `LINT_FAILURE`: ESLint / Flake8 code style violations.
- `DEPENDENCY_ERROR`: npm / pip dependency installation errors.
- `CONFIGURATION_ERROR`: Missing configuration files / env vars.
- `TIMEOUT`: Command exceeded runtime execution timeout limit.
- `RESOURCE_LIMIT`: OOM / Memory limit exceeded.
- `UNKNOWN`: Insufficient evidence or unclassified failure.

### Diagnostic Extraction
Errors are parsed to extract:
- `message`: Clear error description.
- `file`: Mapped relative filepath in repository tree.
- `line` & `column`: Line and column numbers.
- `code`: Diagnostic error code (e.g. `TS2532`).
- `source`: Diagnostic stream (`stdout` or `stderr`).

---

## 4. Repair Policy & Decision Matrix

`RepairPolicy` evaluates `ValidationResult` and `AgentState` history to decide the next action:

```
PASSED                    ➔ CONTINUE / SUCCESS
Known Code Failure        ➔ FIX
Transient Network/Sandbox ➔ RETRY
Repeated Same Failure     ➔ HUMAN_REVIEW
Sandbox Blocked           ➔ STOP
Repeated Timeout          ➔ STOP
Repeated Resource Limit   ➔ STOP
Unknown Failure           ➔ HUMAN_REVIEW
```

### Repeated Failure Protection
If the agent produces the exact same diagnostic on the exact same line of the same file more than `MAX_SAME_FAILURE_RETRIES` (2) times:
1. Self-correction is immediately halted.
2. `stop_reason` is set to `MAX_SAME_FAILURE_RETRIES_EXCEEDED`.
3. Agent statustransitions to `AWAITING_HUMAN_REVIEW`.

---

## 5. Validation Planner

`ValidationPlanner` orders validation commands intelligently based on modified files and previous failure modes:

1. **Targeted First**:
   - TypeScript edits ➔ `TYPECHECK` first
   - Test edits ➔ `TEST` first
   - Build file edits ➔ `BUILD` first
   - Lint issues ➔ `LINT` first
2. **Broader Validation**: Before completing a run, broader project validation (`TEST`, `TYPECHECK`, `BUILD`) is executed according to project metadata.

---

## 6. Human Review Gates & Approval Rules

Human approval remains **MANDATORY** in DevOnCall.

The agent enters `AWAITING_HUMAN_REVIEW` when:
- Identical failure repeats > 2 times.
- Failure classification is `UNKNOWN`.
- Sandbox execution is `BLOCKED`.
- Architectural changes are required.

Even when all tests and validations `PASS`, PR creation requires explicit human approval via POST `/api/v1/agent/runs/{id}/approve`.

---

## 7. Production Safety Rules

- `PRODUCTION` permission remains **DENIED**.
- Production database mutation is **PROHIBITED**.
- Host machine command execution is **PROHIBITED** (all validation runs in Docker/Mock sandboxes).
- GitHub PR creation is gated behind explicit human approval.

---

## 8. Integration Architecture

- **Phase 3 Integration**: Code modifications flow through workspace creation, sandbox validation, diagnostic feedback, bounded repair, and human-approved PR creation.
- **Phase 4 Integration**: Sentry incident investigations produce proposed fixes that auto-trigger Phase 6 self-correcting validation runs.
