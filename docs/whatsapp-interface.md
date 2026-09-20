# DevOnCall — Phase 8 Documentation
## WhatsApp Developer Interface Architecture & Specification

### 1. Overview
DevOnCall Phase 8 introduces an official, secure WhatsApp interface that transforms DevOnCall into a mobile on-call developer assistant. Developers can receive incident notifications, inspect stack traces, trigger automated root-cause investigations, request fixes, monitor sandbox and Playwright validation attempts, and review or approve Pull Requests directly from WhatsApp.

---

### 2. Provider Abstraction & Official Meta API Boundary
- **`BaseWhatsAppProvider`**: Abstract interface defining message delivery contracts.
- **`WhatsAppCloudClient`**: Official Meta WhatsApp Cloud API integration boundary (`v18.0`/`v19.0`). Communicates with `https://graph.facebook.com/v18.0/{phone_number_id}/messages`.
- **`MockWhatsAppProvider`**: Offline deterministic simulation provider for testing without a live Meta setup.
- **Strict Prohibition**: DevOnCall NEVER uses WhatsApp Web scraping, QR code automation, or browser control.

---

### 3. Security Architecture & Threat Mitigation

#### 3.1 Identity Verification & Authorization Matrix
Receiving a message from a phone number is **NOT** proof of authorization.
- Every phone number is hashed using SHA256 (`HMAC_SHA256(phone_number, APP_SECRET)`).
- The hash is matched against `AuthorizedDeveloperModel`.
- Authorization is evaluated based on fine-grained roles:
  - `VIEWER`: Read-only access to incidents and status (`HELP`, `INCIDENTS`, `INCIDENT`, `STATUS`).
  - `DEVELOPER`: Viewer access + trigger investigation, propose fix, view validation (`INVESTIGATE`, `FIX`, `VALIDATION`).
  - `APPROVER`: Developer access + approve/reject Pull Request creation (`APPROVE`, `REJECT`).
  - `ADMIN`: Full developer administration.

#### 3.2 Single-Use Short-Lived Confirmation Tokens
High-impact commands (`FIX`, `APPROVE`, `REJECT`) DO NOT execute immediately.
- DevOnCall generates a 6-character single-use alphanumeric token (e.g., `A1B2C3`).
- Token expires in **10 minutes**.
- Action executes ONLY when developer sends `CONFIRM A1B2C3`.
- Replaying or reusing a token returns an error.

#### 3.3 Prompt Injection Guard
Raw WhatsApp text is untrusted input.
- `WhatsAppSecurityPolicy.sanitize_input()` scans text for injection attempts (`"IGNORE ALL PREVIOUS INSTRUCTIONS"`, `"SYSTEM PROMPT"`, `"DELETE FROM"`).
- Malicious patterns are stripped or neutralized before command parsing.

#### 3.4 Secret Redaction
- `WhatsAppResponseRedactor` scrubs API keys (`devoncall_sec_*`), GitHub tokens (`ghp_*`), JWTs, and internal database connection strings before outgoing transmission.

#### 3.5 Production Deployment Boundary
- `PRODUCTION` deployment permissions are **STRICTLY DENIED** across all roles in Phase 8.
- Pull Requests require human approval and merge via GitHub.

---

### 4. Command Grammar & Parser Syntax

| Command | Usage | Description |
| :--- | :--- | :--- |
| `HELP` | `HELP` | Display list of supported commands and active role |
| `STATUS` | `STATUS` | Check system health, database, sandbox & WhatsApp provider status |
| `INCIDENTS` | `INCIDENTS` | List active open production incidents |
| `INCIDENT <ID>` | `INCIDENT 142` | Inspect incident summary, stack trace, and culprit |
| `DETAILS <ID> [PAGE]`| `DETAILS 142 2` | Paginated full stack trace and metadata breakdown |
| `INVESTIGATE <ID>`| `INVESTIGATE 142` | Trigger agent root-cause investigation |
| `FIX <ID>` | `FIX 142` | Propose fix & generate confirmation token |
| `CONFIRM <TOKEN>`| `CONFIRM A1B2C3` | Confirm queued fix or PR creation action |
| `CANCEL` | `CANCEL` | Cancel pending confirmation request |
| `VALIDATION <ID>` | `VALIDATION 142` | Check sandbox & browser validation attempt results |
| `APPROVE <ID>` | `APPROVE 142` | Request confirmation token to approve PR creation |
| `REJECT <ID>` | `REJECT 142` | Reject proposed fix or close incident investigation |
| `PROJECT [ID]` | `PROJECT 1` | Switch or view active project binding |
| `WHOAMI` | `WHOAMI` | Display registered developer profile, phone & role |
| `STOP` | `STOP` | Pause WhatsApp notifications |

---

### 5. API Endpoints

- `GET /api/v1/webhooks/whatsapp`: Meta Webhook challenge verification endpoint.
- `POST /api/v1/webhooks/whatsapp`: Meta Webhook event receiver (with HMAC SHA256 verification).
- `GET /api/v1/whatsapp/status`: Provider status & developer stats.
- `GET /api/v1/whatsapp/developers`: List authorized developers.
- `POST /api/v1/whatsapp/developers`: Register new authorized developer.
- `POST /api/v1/whatsapp/simulate`: Offline command simulator runner.
- `GET /api/v1/whatsapp/conversations`: View active conversations and message history.
