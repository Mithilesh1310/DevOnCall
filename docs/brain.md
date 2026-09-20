# Project Brain — Living Engineering Memory (Phase 10)

DevOnCall Project Brain is a persistent, queryable knowledge layer that maintains structured knowledge about a repository, its monorepo architecture, services, dependencies, database schemas, incidents, root causes, fixes, validation results, staging deployments, and engineering decisions.

---

## 1. Core Architecture

Project Brain stores structured knowledge as a typed graph composed of **Nodes**, **Edges** (relationships), and an **Event Ledger**.

```
                           PROJECT BRAIN ARCHITECTURE
                           
      [Repository Scan]    [Incident Pipeline]    [Sandbox Validation]    [Staging Gate]
              │                     │                      │                    │
              ▼                     ▼                      ▼                    ▼
     ┌────────────────────────────────────────────────────────────────────────────────┐
     │                             RepositoryBrainExtractor                           │
     └──────────────────────────────────────┬─────────────────────────────────────────┘
                                            │
                                            ▼
     ┌────────────────────────────────────────────────────────────────────────────────┐
     │                     BrainSecretRedactor & ConfidenceEvaluator                  │
     └──────────────────────────────────────┬─────────────────────────────────────────┘
                                            │
                                            ▼
     ┌────────────────────────────────────────────────────────────────────────────────┐
     │                      BrainUpdater (Deduplication via Keys)                     │
     └──────────────────────────────────────┬─────────────────────────────────────────┘
                                            │
                      ┌─────────────────────┼─────────────────────┐
                      ▼                     ▼                     ▼
              ProjectBrainNode      ProjectBrainEdge      ProjectBrainEvent
                 (Fact Graph)         (Graph Edges)          (Audit Ledger)
```

---

## 2. Knowledge Node Types (`BrainNodeType`)

| Node Type | Description | Key Format Example |
| :--- | :--- | :--- |
| `PROJECT` | Monorepo root container & GitHub metadata | `project:demo-project` |
| `SERVICE` | Monorepo application/service boundary | `service:apps/api` |
| `REPOSITORY` | Repository structure and branch tracking | `repo:devoncall` |
| `FILE` | Core source or configuration file | `file:apps/api/app/main.py` |
| `FUNCTION` | Specific handler or function entrypoint | `function:main.py:get_status` |
| `DATABASE` | Database engine & Alembic schema state | `database:alembic_postgres` |
| `INCIDENT` | Sentry incident ingested record | `incident:inc-101` |
| `ROOT_CAUSE` | Root-cause hypothesis & stack frame evidence | `root_cause:inc-101` |
| `FIX` | Proposed or committed code modification | `fix:inc-101` |
| `VALIDATION` | Test, build, typecheck, or browser result | `validation:val-101` |
| `DEPLOYMENT` | Staging deployment gate record | `deployment:stg-101` |
| `DECISION` | Engineering decision or policy rule | `decision:policy-1` |

---

## 3. Strict Provenance & Confidence Evaluation

Every fact in Project Brain records explicit **Provenance** (`source_type` and `source_reference`) and a **Confidence Rating**:

### Provenance Sources (`BrainSourceType`)
- `REPOSITORY_SCAN`: Deterministic repository scan / snapshot.
- `INCIDENT`: Sentry incident ingestion pipeline.
- `VALIDATION`: Sandbox automated test / lint / typecheck run.
- `STAGING`: Staging deployment verification gate.
- `HUMAN`: Explicit human input or approval.
- `SYSTEM`: System generated event or inference.

### Confidence Hierarchy (`BrainConfidence`)
- `VERIFIED`: High-certainty facts directly verified by deterministic repository scan or human explicitly.
- `HIGH`: Confirmed by sandbox test execution or staging health checks.
- `MEDIUM`: Stack trace root-cause hypothesis or initial incident correlation.
- `LOW`: Tentative inference or single unverified signal.
- `UNKNOWN`: Unclassified source.

---

## 4. Secret Redaction (`BrainSecretRedactor`)

Before any node content, metadata payload, or event record is committed to Postgres database or returned over APIs/WhatsApp, `BrainSecretRedactor` automatically scrubs:
- Database passwords (`postgres://user:password@...`)
- GitHub Personal Access Tokens (`ghp_...`)
- AWS Access Keys (`AKIA...`)
- API Secret Keys (`sk-proj-...`)
- Sensitive keys (`password`, `api_key`, `token`, `secret`, `privkey`)

---

## 5. Agent Integration (`project_brain_query`)

DevOnCall agents access Project Brain via the `project_brain_query` tool registered in `ToolRegistry`:

- **Permission Level**: `READ_ONLY` (Agents cannot mutate brain graph directly).
- **Execution Flow**:
  1. Agent calls `project_brain_query(project_id="demo-project", query="user auth")`.
  2. Query Engine filters nodes by keyword and returns matched nodes, edges, and confidence badges.
  3. Agent incorporates verified architecture and incident history into its investigation plan.

---

## 6. WhatsApp Commands (`BRAIN`)

Developers can query Project Brain directly via WhatsApp:

- `BRAIN` or `BRAIN SUMMARY`: Returns total nodes, relationships, verified facts, services, and incidents.
- `BRAIN SEARCH <query>`: Queries engineering memory for specific services or keywords.
- `BRAIN INCIDENTS`: Retrieves historical incident and fix records.

All WhatsApp responses are automatically redacted and governed by `WhatsAppSecurityPolicy`.

---

## 7. REST API Endpoints

- `GET /api/v1/brain/summary?project_id={id}`
- `GET /api/v1/brain/query?project_id={id}&query={text}`
- `GET /api/v1/brain/nodes?project_id={id}&node_type={type}`
- `GET /api/v1/brain/relationships?project_id={id}`
- `GET /api/v1/brain/history?project_id={id}`
- `POST /api/v1/projects/{project_id}/brain/rebuild`
