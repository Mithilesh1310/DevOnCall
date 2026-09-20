# DevOnCall Phase 7 — Playwright Browser Verification + UI Testing Agent

This document details the architecture, security policy, scenario model, provider abstraction, artifact management, failure classification, and agent integration for Phase 7 of DevOnCall.

---

## 1. Objective & Loop

Phase 7 extends DevOnCall to verify web applications through an isolated browser execution loop:

```
CODE ➔ SANDBOX ➔ START APPLICATION (HEALTH CHECK) ➔ STAGING DEPLOYMENT ➔ PLAYWRIGHT BROWSER VERIFICATION ➔ INTERACT & ASSERT ➔ CAPTURE CONSOLE / NETWORK / SCREENSHOT ➔ FAILURE CLASSIFIER ➔ REPAIR POLICY ➔ FIX / RETEST ➔ HUMAN APPROVAL ➔ PR
```

The browser is used strictly for development and Phase 9 staging-style verification of application UI workflows against allocated staging URLs e.g. `http://127.0.0.1:<port>`.


---

## 2. Security Boundaries & Protection Rules

Phase 7 enforces strict security controls:

- **Target URL Allowlist**: Navigation is restricted exclusively to configured base URLs (`BROWSER_ALLOWED_BASE_URLS`, e.g. `http://localhost:3000`).
- **Forbidden Protocols**: Rejects `file://`, `chrome://`, `data:`, `devtools://`, `javascript:`, `about:`.
- **Cloud Metadata Protection**: Rejects requests to `169.254.169.254`, `metadata.google.internal`, and cloud provider metadata IPs.
- **Infrastructure Port Protection**: Blocks access to internal service ports (22 SSH, 5432 Postgres, 6379 Redis, 27017 Mongo).
- **No Production Access**: Production browser access, production credentials, CAPTCHA bypass, and MFA harvesting are **PROHIBITED**. `PRODUCTION` permission remains **DENIED**.
- **No Arbitrary Code Execution**: `eval()` or arbitrary JavaScript from HTTP inputs is rejected.
- **Credential Redaction**: Passwords, tokens, cookies, secrets, and authorization headers are automatically redacted from logs, outputs, and screenshots.
- **Path Traversal Protection**: Screenshot and log artifact saving verifies that target paths stay inside designated workspace artifact directories.

---

## 3. Architecture & Provider Abstraction

The service layer is located in `apps/api/app/services/browser/`:

```
Agent / ToolRegistry
       │
       ▼
BrowserValidationTool (browser_validate)
       │
       ▼
BrowserManager (Health Check & Lifecycle)
       │
       ├───────────────────────────────┐
       ▼                               ▼
MockBrowserProvider            PlaywrightBrowserProvider
(Offline Scenarios A-F)        (Real Playwright Engine)
```

### Provider Model:
1. `MockBrowserProvider`: Deterministic mock provider for offline tests and headless verification without browser binaries.
2. `PlaywrightBrowserProvider`: Real Chromium/Firefox/WebKit execution using Playwright's `async_api`. If Playwright binaries are unavailable on the host, cleanly reports `PLAYWRIGHT RUNTIME = BLOCKED`.

---

## 4. Scenario & Selector Model

### Browser Actions:
- `NAVIGATE`: Open relative or allowed target URL.
- `CLICK`: Click an element matching a selector.
- `FILL`: Fill form inputs with values (redacted if sensitive).
- `SELECT`: Choose option in select element.
- `ASSERT_VISIBLE`: Verify element visibility.
- `ASSERT_TEXT`: Verify text matches expected value.
- `ASSERT_URL`: Verify current page URL path.
- `WAIT_FOR`: Pause or wait for element appearance.
- `SCREENSHOT`: Capture page viewport screenshot.

### Selector Strategy:
Selectors are checked and tagged in order of stability preference:
1. `DATA_TESTID` (`[data-testid='...']`)
2. `ACCESSIBLE_ROLE` (`[role='...']`)
3. `LABEL` (`[name='...']`)
4. `STABLE_CSS` (clean CSS selectors)
5. `FRAGILE_CSS` (flagged if using `:nth-child` or generated hash classnames)

---

## 5. Artifact Management

`BrowserArtifactManager` manages screenshot, console, and network logs:

- `MAX_SCREENSHOT_SIZE_MB = 5`
- `MAX_CONSOLE_EVENTS = 100`
- `MAX_CONSOLE_OUTPUT_BYTES = 50000`

All saved logs undergo credential redaction before disk storage.

---

## 6. Failure Classification & Repository Correlation

`BrowserFailureClassifier` classifies browser run outcomes into structured failure types:
- `ELEMENT_NOT_FOUND`
- `ASSERTION_FAILED`
- `NAVIGATION_FAILED`
- `TIMEOUT`
- `CONSOLE_ERROR`
- `NETWORK_ERROR`
- `APPLICATION_ERROR`
- `BROWSER_CRASH`
- `BLOCKED_URL`
- `SCENARIO_INVALID`
- `APPLICATION_NOT_READY`
- `UNKNOWN`

If a network 500 error or console exception occurs (e.g. `POST /api/login`), the classifier correlates the endpoint with repository files (`apps/api/app/api/login.py`) to guide agent self-correction.

---

## 7. Bounded Execution Limits & Repair Policy

Browser runs are bounded to prevent execution runaway:
- `MAX_BROWSER_RUNS = 5` per agent task.
- Reaches `AWAITING_HUMAN_REVIEW` if browser limits are exceeded or same failure repeats.
- Human approval gate remains **MANDATORY** before PR creation.
