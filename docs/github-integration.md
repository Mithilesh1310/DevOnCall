# GitHub Integration & Repository Intelligence Specification

This document details the architectural design, security model, mock provider setup, deterministic repository inspection algorithm, and snapshot schema for **DevOnCall Phase 1**.

---

## 1. Overview & Architecture

DevOnCall connects to GitHub repositories via a modular integration layer (`apps/api/app/services/integrations/github/`).

```
                    ┌─────────────────────────┐
                    │ Next.js Web Dashboard   │
                    └────────────┬────────────┘
                                 │ REST API
                                 ▼
                    ┌─────────────────────────┐
                    │    FastAPI Endpoints    │
                    │ (/api/v1/github/...)    │
                    └────────────┬────────────┘
                                 │
                     ┌───────────┴───────────┐
                     ▼                       ▼
            [ MockGitHubProvider ]   [ GitHubProvider ]
            (Development / Testing)   (Production OAuth)
                     │                       │
                     └───────────┬───────────┘
                                 │ Raw Tree & Metadata
                                 ▼
                     ┌───────────────────────┐
                     │ RepositoryInspector   │
                     │ (Deterministic Engine)│
                     └───────────┬───────────┘
                                 │ RepositorySnapshot
                                 ▼
                     ┌───────────────────────┐
                     │ PostgreSQL (Project)  │
                     └───────────────────────┘
```

---

## 2. Authentication & Token Security Model

### Strict Security Rules:
1. **No Frontend Exposure**: GitHub OAuth client secrets, private keys, and user access tokens are processed exclusively server-side in FastAPI. They are never sent to Next.js client-side JS, browser `localStorage`, or `sessionStorage`.
2. **No Plaintext Token Storage**: Access tokens are not saved directly in the `projects` table. Token storage interfaces are separated from project entity metadata.
3. **Environment Variable Injection**: Configured via Pydantic `BaseSettings` (`GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `GITHUB_REDIRECT_URI`).

---

## 3. Development Mock Provider (`MockGitHubProvider`)

To allow instant local development and test execution without requiring real GitHub credentials:
- Set `USE_MOCK_GITHUB=true` in `.env`.
- Emulates GitHub API endpoints for synthetic repositories such as `mock-owner/devoncall-demo`.
- Returns realistic manifest files (`package.json`, `next.config.js`, `pyproject.toml`, `Dockerfile`, `docker-compose.yml`, `README.md`).

---

## 4. Deterministic Repository Inspection Algorithm

The `RepositoryInspector` analyzes file tree metadata using strict, deterministic rule sets **without using LLMs**:

1. **Tree Sanitization & Limit Enforcement**:
   - Excludes heavy/generated paths (`node_modules/`, `.git/`, `.next/`, `dist/`, `build/`, `venv/`, `__pycache__`).
   - Maximum tree entries processed: `2,500`.
   - Maximum path depth: `10`.
   - Maximum path length: `256` characters.
2. **Manifest & Directory Classification**:
   - Identifies important configuration manifests (`package.json`, `pyproject.toml`, `Dockerfile`, `docker-compose.yml`, `tsconfig.json`).
   - Classifies source directories (`src/`, `app/`, `pages/`, `components/`, `lib/`, `api/`) and test directories (`tests/`, `test/`, `__tests__/`).
3. **Framework & Runtime Detection Rules**:
   - **Next.js**: `package.json` + `next.config.*` -> Status: `DETECTED` (Confidence: 1.0)
   - **FastAPI**: `pyproject.toml`/`requirements.txt` + `main.py` -> Status: `DETECTED` (Confidence: 0.9)
   - **Node.js / npm / pnpm**: `package.json` + `package-lock.json`/`pnpm-lock.yaml` -> Status: `DETECTED` (Confidence: 1.0)
   - **Docker**: `Dockerfile` or `docker-compose.yml` -> Status: `DETECTED` (Confidence: 1.0)

---

## 5. RepositorySnapshot Schema

```json
{
  "owner": "mock-owner",
  "repo": "devoncall-demo",
  "default_branch": "main",
  "commit_sha": "a1b2c3d4e5f67890123456789abcdef012345678",
  "url": "https://github.com/mock-owner/devoncall-demo",
  "total_files": 28,
  "total_directories": 12,
  "detected_languages": ["JavaScript", "Python", "TypeScript"],
  "detections": [
    {
      "name": "Next.js",
      "type": "framework",
      "status": "DETECTED",
      "confidence": 1.0,
      "evidence": ["package.json present", "next.config file found"]
    },
    {
      "name": "FastAPI",
      "type": "framework",
      "status": "DETECTED",
      "confidence": 0.9,
      "evidence": ["Python project manifest present", "API structure detected"]
    }
  ],
  "important_files": ["package.json", "pyproject.toml", "Dockerfile", "docker-compose.yml"],
  "source_directories": ["src", "app"],
  "test_directories": ["tests"],
  "configuration_files": ["next.config.js", "tsconfig.json"],
  "tree": [
    { "path": "package.json", "name": "package.json", "type": "file", "size": 1200 },
    { "path": "apps", "name": "apps", "type": "directory", "children": [] }
  ],
  "inspected_at": "2026-09-20T13:25:00Z"
}
```
