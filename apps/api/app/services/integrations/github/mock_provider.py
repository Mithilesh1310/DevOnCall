import logging
from typing import List, Dict, Any
from app.services.integrations.git_base import BaseGitProvider
from app.schemas.repository import RepositoryMetadata, GitHubRepoSummary

logger = logging.getLogger("devoncall.integrations.github.mock")

class MockGitHubProvider(BaseGitProvider):
    """
    Deterministic Mock GitHub Provider for credential-free local development and automated testing.
    Emulates GitHub API responses for 'mock-owner/devoncall-demo' and 'mock-owner/fastapi-service'.
    """

    @property
    def provider_name(self) -> str:
        return "mock-github"

    async def is_authenticated(self) -> bool:
        return True

    async def list_repositories(self) -> List[GitHubRepoSummary]:
        return [
            GitHubRepoSummary(
                id="mock-repo-101",
                owner="mock-owner",
                name="devoncall-demo",
                full_name="mock-owner/devoncall-demo",
                default_branch="main",
                html_url="https://github.com/mock-owner/devoncall-demo",
                is_private=False,
                description="DevOnCall Sample Production Workload (Next.js + FastAPI + Docker)"
            ),
            GitHubRepoSummary(
                id="mock-repo-102",
                owner="mock-owner",
                name="payment-service",
                full_name="mock-owner/payment-service",
                default_branch="main",
                html_url="https://github.com/mock-owner/payment-service",
                is_private=True,
                description="Backend Microservice (Python FastAPI + PostgreSQL + Redis)"
            )
        ]

    async def get_repository_metadata(self, owner: str, repo: str) -> RepositoryMetadata:
        logger.info(f"[MOCK GITHUB] Fetching metadata for {owner}/{repo}")
        return RepositoryMetadata(
            owner=owner,
            repo=repo,
            default_branch="main",
            commit_sha="a1b2c3d4e5f67890123456789abcdef012345678",
            html_url=f"https://github.com/{owner}/{repo}",
            is_private=False
        )

    async def get_repository_tree(self, owner: str, repo: str, branch: str) -> List[Dict[str, Any]]:
        logger.info(f"[MOCK GITHUB] Fetching deterministic git tree for {owner}/{repo} branch {branch}")
        
        if "payment" in repo:
            return [
                {"path": "pyproject.toml", "type": "blob", "size": 450},
                {"path": "requirements.txt", "type": "blob", "size": 180},
                {"path": "Dockerfile", "type": "blob", "size": 320},
                {"path": "docker-compose.yml", "type": "blob", "size": 520},
                {"path": "README.md", "type": "blob", "size": 1200},
                {"path": ".gitignore", "type": "blob", "size": 150},
                {"path": "app", "type": "tree"},
                {"path": "app/__init__.py", "type": "blob", "size": 40},
                {"path": "app/main.py", "type": "blob", "size": 850},
                {"path": "app/db.py", "type": "blob", "size": 600},
                {"path": "tests", "type": "tree"},
                {"path": "tests/test_api.py", "type": "blob", "size": 400},
            ]

        # Default 'devoncall-demo' monorepo mock tree
        return [
            {"path": "package.json", "type": "blob", "size": 1200},
            {"path": "package-lock.json", "type": "blob", "size": 15400},
            {"path": "tsconfig.json", "type": "blob", "size": 650},
            {"path": "next.config.js", "type": "blob", "size": 240},
            {"path": "Dockerfile", "type": "blob", "size": 480},
            {"path": "docker-compose.yml", "type": "blob", "size": 890},
            {"path": "README.md", "type": "blob", "size": 2100},
            {"path": ".gitignore", "type": "blob", "size": 310},
            {"path": "apps", "type": "tree"},
            {"path": "apps/web", "type": "tree"},
            {"path": "apps/web/package.json", "type": "blob", "size": 800},
            {"path": "apps/web/next.config.js", "type": "blob", "size": 150},
            {"path": "apps/web/src", "type": "tree"},
            {"path": "apps/web/src/app", "type": "tree"},
            {"path": "apps/web/src/app/page.tsx", "type": "blob", "size": 1800},
            {"path": "apps/web/src/components", "type": "tree"},
            {"path": "apps/web/src/components/Header.tsx", "type": "blob", "size": 950},
            {"path": "apps/api", "type": "tree"},
            {"path": "apps/api/pyproject.toml", "type": "blob", "size": 620},
            {"path": "apps/api/requirements.txt", "type": "blob", "size": 210},
            {"path": "apps/api/app", "type": "tree"},
            {"path": "apps/api/app/main.py", "type": "blob", "size": 1100},
            {"path": "apps/api/tests", "type": "tree"},
            {"path": "apps/api/tests/test_health.py", "type": "blob", "size": 350},
            {"path": "packages", "type": "tree"},
            {"path": "packages/shared", "type": "tree"},
            {"path": "packages/shared/package.json", "type": "blob", "size": 250},
            {"path": "packages/shared/src", "type": "tree"},
            {"path": "packages/shared/src/index.ts", "type": "blob", "size": 890},
        ]
