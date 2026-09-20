# DevOnCall 🤖

**DevOnCall** is an autonomous AI Production Software Engineer platform designed to monitor, investigate, reproduce, fix, test, and stage resolutions for software production incidents.

> **Product Vision**: User / Sentry / Alert → DevOnCall → Investigate production incident → Understand codebase → Reproduce safely → Fix → Test → Staging → Human approval → Production.

---

## 📌 Current Status: Phase 12 Active — Controlled Canary Deployment & Production Safety Gate

Phase 12 builds DevOnCall's **Controlled Production Release Gate**.

### Features in Phase 12:
- **Approval-Gated State Machine (`apps/api/app/services/deployment/`)**: `CREATED` → `STAGING_PASSED` → `AWAITING_APPROVAL` → `APPROVED` → `CANARY_DEPLOYED` → `CANARY_VERIFIED` → `APPROVED` → `DEPLOYED` / `ROLLED_BACK`.
- **Double Human Approval Gates**: Gate 1 for 1-10% Canary Release approval; Gate 2 for Full Production Deployment approval following Canary Decision Engine PASS.
- **Canary Traffic Bounds**: Bounded strictly between **1.0%** and **10.0%**. Rejects invalid traffic inputs.
- **Canary Decision Engine (`CanaryDecisionEngine`)**: Evaluates real-time telemetry against baseline error rates (+0.5% max diff), latency p95 (+20% max diff), and latency p99 (+25% max diff). Rejects converting `INSUFFICIENT_DATA` into `PASS`.
- **Emergency & Automated Rollback (`RollbackService`)**: Immediate, approval-supported automated or manual rollbacks requiring exact 40-character target commit SHAs.
- **Provider Abstraction (`BaseDeploymentProvider`)**: `MockDeploymentProvider` for test scenarios; `ProductionProvider` for real environment release APIs without shell execution.
- **Credential Isolation & Safety Policy**: Credentials reside strictly inside deployment adapters. LLM agents receive **ZERO** direct production write permissions.
- **Read-Only Agent Tools (`deployment_tools.py`)**: `release_candidate_status`, `canary_verification_details`, `deployment_audit_log` registered with `ToolPermission.READ_ONLY`.
- **WhatsApp Integration**: Supports `RELEASES`, `CANARY <rc_id>`, `APPROVE CANARY <rc_id> <token>`, `APPROVE PRODUCTION <rc_id> <token>`, `REJECT RELEASE <rc_id>`, and `APPROVE ROLLBACK <rc_id> <token>` commands.
- **Releases Dashboard UI (`/releases`)**: Next.js UI showing active candidates queue, gate steppers, traffic bounding controls, telemetry metrics comparison, decision engine verdicts, and rollback modal.
- **Alembic Database Migration (`0013_controlled_canary_deployment.py`)**: Creates 7 production release gate tables with proper indexes.




---

## 🏗️ Monorepo Architecture & Structure

```
devoncall/
│
├── apps/
│   ├── web/            # Next.js + TypeScript + Tailwind CSS Dashboard
│   └── api/            # FastAPI + Python 3.11+ Backend Service
│
├── packages/
│   ├── shared/         # Shared TypeScript interfaces & schemas
│   └── config/         # Shared tooling configurations
│
├── workspaces/         # Isolated per-run git workspace directories
│
├── infrastructure/
│   └── docker/         # Production Dockerfiles (Dockerfile.api, Dockerfile.web)
│
├── docs/               # Technical specifications (docs/architecture.md, docs/sentry-integration.md, docs/incident-intelligence.md)
├── scripts/            # Utility runner scripts
├── tests/              # Monorepo tests
│
├── .env.example        # Environment variable templates
├── docker-compose.yml  # Local multi-container Docker deployment
└── README.md           # Master repository documentation
```

---

## 🚀 Quickstart & Local Setup

### Option 1: Local CLI Setup

#### 1. Environment Setup
```bash
cp .env.example .env
```

#### 2. Backend API (`apps/api`) Setup
```bash
cd apps/api
python -m venv .venv
# On Windows: .venv\Scripts\activate | On Unix: source .venv/bin/activate
pip install -e .[dev]
uvicorn app.main:app --reload --port 8000
```

#### 3. Frontend (`apps/web`) Setup
```bash
cd apps/web
npm install
npm run dev
```

---

## 🧪 Running Tests

Run the full automated pytest suite:

```powershell
.\.venv\Scripts\python.exe -m pytest apps/api/tests -v
```

---

## 🔑 Environment Variables

| Variable | Default Value | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/devoncall` | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis cache & queue connection string |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API URL for frontend queries |
| `PORT` | `8000` | FastAPI HTTP server port |
| `ENVIRONMENT` | `development` | Runtime environment mode |
