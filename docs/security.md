# DevOnCall — Security Policy & Controls

DevOnCall implements multi-layered security controls to ensure autonomous agent actions are bounded, deterministic, and isolated.

---

## 1. Core Security Guarantees

1. **`PRODUCTION = DENIED` Policy**:
   - DevOnCall NEVER deploys code directly to production environments.
   - Production modifications, Kubernetes cluster mutations, production rollbacks, or autonomous production actions are strictly **DENIED** with HTTP 403 / `SECURITY_POLICY_VIOLATION`.

2. **Branch Protection**:
   - Default target branch (`main`, `master`, `develop`) is dynamically retrieved from GitHub project metadata.
   - Direct commits to configured default branches are strictly blocked.
   - Agent commits are created exclusively on isolated feature branches (`devoncall/agent/<run_id>`).

3. **Isolated Docker Sandbox & Staging Environments**:
   - Code building, testing, linting, and staging deployments run inside isolated Docker containers with non-root privileges.
   - Containers execute in dedicated bridge networks (`sandbox-net-<id>`, `staging-net-<id>`) with access strictly restricted to allowlisted endpoints.

4. **Secret & Credential Scrubbing**:
   - `BrainSecretRedactor` automatically scrubs passwords, API keys (`sk-...`), GitHub tokens (`ghp_...`), AWS keys (`AKIA...`), and database connection URIs before persistence or API/WhatsApp output.

5. **Project Brain Read-Only Querying**:
   - The agent tool `project_brain_query` is configured with `ToolPermission.READ_ONLY`.
   - Agents cannot mutate Project Brain memory or inject unauthorized knowledge nodes.

6. **Production Telemetry Observability Boundary**:
   - Production telemetry ingestion, observation lookup, and incident intelligence reports strictly enforce `PRODUCTION = READ_ONLY`.
   - Production shell execution, filesystem/database writes, container restarts, production deployments, or rollbacks are hard-rejected with `SECURITY_POLICY_VIOLATION`.
   - Agent tools (`production_incident_search`, `production_incident_details`, `production_incident_correlate`) are strictly `READ_ONLY`.

7. **WhatsApp Security Policy**:
   - HMAC SHA256 hashed phone number identity verification.
   - Short-lived, single-use confirmation tokens for sensitive actions (`FIX`, `CONFIRM`, `APPROVE`).
   - Prompt injection detector neutralizes malicious text payloads.

8. **Human Approval Gate**:
   - Pull Request creation requires explicit human review and approval.

9. **Phase 12 Controlled Production Release Gate**:
   - Production operations are ONLY allowed through an explicit double-human approval gated state machine (`CREATED` → `STAGING_PASSED` → `AWAITING_APPROVAL` → `APPROVED` → `CANARY_DEPLOYED` → `CANARY_VERIFIED` → `APPROVED` → `DEPLOYED` / `ROLLED_BACK`).
   - Gate 1 requires explicit human approval for Canary release (1-10% traffic).
   - Gate 2 requires explicit human approval for Full Production deployment after Canary Decision Engine verdict `PASS`.
   - Single-use, cryptographically generated 10-minute confirmation tokens are required for all approvals and rollbacks.
   - Requires exact 40-character hexadecimal git commit SHA; floating tags (`latest`, `main`, `master`) are rejected.
   - Credentials are isolated inside `BaseDeploymentProvider` adapters and never exposed to agent runtime, Project Brain, LLM prompts, or WhatsApp.
   - LLM agent deployment tools (`release_candidate_status`, `canary_verification_details`, `deployment_audit_log`) are strictly `ToolPermission.READ_ONLY`.

