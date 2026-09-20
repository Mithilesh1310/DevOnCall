import logging
import base64
from typing import List, Dict, Any, Optional
import httpx
from fastapi import HTTPException, status
from app.config import settings
from app.services.integrations.git_base import BaseGitProvider
from app.schemas.repository import RepositoryMetadata, GitHubRepoSummary

logger = logging.getLogger("devoncall.integrations.github")


class GitHubProvider(BaseGitProvider):
    """
    Production-ready GitHub API Client implementation using HTTPX async client.
    Handles authentication, error mapping, rate-limits, and response parsing.
    """

    def __init__(self, access_token: str | None = None):
        self.access_token = access_token or getattr(settings, "GITHUB_TOKEN", None)
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "DevOnCall-Production-Engineer/0.1"
        }
        if self.access_token:
            self.headers["Authorization"] = f"Bearer {self.access_token}"

    @property
    def provider_name(self) -> str:
        return "github"

    async def is_authenticated(self) -> bool:
        return bool(self.access_token)

    async def get_authenticated_user(self) -> Dict[str, Any]:
        """
        Retrieves identity details for the authenticated user or OAuth/App token.
        """
        if not self.access_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="GitHub access token missing.")

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(f"{self.base_url}/user", headers=self.headers)
                self._check_rate_limit(resp)
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "login": data.get("login"),
                        "id": data.get("id"),
                        "type": data.get("type", "User"),
                        "name": data.get("name"),
                        "email": data.get("email"),
                    }
                else:
                    raise HTTPException(
                        status_code=resp.status_code,
                        detail=f"GitHub API Error verifying authenticated identity: HTTP {resp.status_code}"
                    )
            except httpx.RequestError as exc:
                logger.error(f"HTTP error verifying GitHub authenticated identity: {exc}")
                raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="GitHub API request timed out")

    async def list_repositories(self) -> List[GitHubRepoSummary]:
        if not self.access_token:
            logger.info("GitHub access token missing. Returning empty repository list.")
            return []

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/user/repos?sort=updated&per_page=100",
                    headers=self.headers
                )
                self._check_rate_limit(response)
                
                if response.status_code != 200:
                    logger.error(f"GitHub API error listing repos. Status: {response.status_code}")
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"GitHub API Error: {response.status_code}"
                    )

                data = response.json()
                return [
                    GitHubRepoSummary(
                        id=str(repo["id"]),
                        owner=repo["owner"]["login"],
                        name=repo["name"],
                        full_name=repo["full_name"],
                        default_branch=repo.get("default_branch", "main"),
                        html_url=repo["html_url"],
                        is_private=repo.get("private", False),
                        description=repo.get("description")
                    )
                    for repo in data
                ]
            except httpx.RequestError as exc:
                logger.error(f"HTTP error contacting GitHub API: {exc}")
                raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="GitHub API request timed out")

    async def get_repository_metadata(self, owner: str, repo: str) -> RepositoryMetadata:
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # 1. Fetch Repository Details
                repo_resp = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}",
                    headers=self.headers
                )
                self._check_rate_limit(repo_resp)

                if repo_resp.status_code == 404:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"GitHub repository {owner}/{repo} not found")
                elif repo_resp.status_code != 200:
                    raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"GitHub API Error: {repo_resp.status_code}")

                repo_data = repo_resp.json()
                default_branch = repo_data.get("default_branch", "main")

                # 2. Fetch Latest Commit SHA for Default Branch
                commit_sha = "head"
                commit_resp = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/commits/{default_branch}",
                    headers=self.headers
                )
                if commit_resp.status_code == 200:
                    commit_sha = commit_resp.json().get("sha", "head")

                return RepositoryMetadata(
                    owner=owner,
                    repo=repo,
                    default_branch=default_branch,
                    commit_sha=commit_sha,
                    html_url=repo_data.get("html_url", f"https://github.com/{owner}/{repo}"),
                    is_private=repo_data.get("private", False)
                )
            except httpx.RequestError as exc:
                logger.error(f"HTTP request error fetching metadata for {owner}/{repo}: {exc}")
                raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="GitHub API request timed out")

    async def get_repository_tree(self, owner: str, repo: str, branch: str) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                url = f"{self.base_url}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
                resp = await client.get(url, headers=self.headers)
                self._check_rate_limit(resp)

                if resp.status_code != 200:
                    logger.error(f"Failed to fetch GitHub git tree for {owner}/{repo} branch {branch}. Status: {resp.status_code}")
                    return []

                tree_data = resp.json().get("tree", [])
                return tree_data
            except httpx.RequestError as exc:
                logger.error(f"HTTP request error fetching tree for {owner}/{repo}: {exc}")
                return []

    async def get_file_content(self, owner: str, repo: str, path: str, ref: str = "main") -> Dict[str, Any]:
        """
        Retrieves file contents and metadata for a specific path and git ref.
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}?ref={ref}"
                resp = await client.get(url, headers=self.headers)
                self._check_rate_limit(resp)

                if resp.status_code == 200:
                    data = resp.json()
                    content_raw = ""
                    if data.get("encoding") == "base64" and data.get("content"):
                        content_raw = base64.b64decode(data["content"]).decode("utf-8", errors="replace")

                    return {
                        "name": data.get("name"),
                        "path": data.get("path"),
                        "sha": data.get("sha"),
                        "size": data.get("size"),
                        "content": content_raw,
                    }
                else:
                    raise HTTPException(
                        status_code=resp.status_code,
                        detail=f"Failed to retrieve file '{path}' from GitHub API (HTTP {resp.status_code})."
                    )
            except httpx.RequestError as exc:
                logger.error(f"HTTP request error fetching file '{path}' for {owner}/{repo}: {exc}")
                raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="GitHub API request timed out")

    async def get_commit(self, owner: str, repo: str, ref: str = "main") -> Dict[str, Any]:
        """
        Retrieves commit metadata for a specific git ref or SHA.
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                url = f"{self.base_url}/repos/{owner}/{repo}/commits/{ref}"
                resp = await client.get(url, headers=self.headers)
                self._check_rate_limit(resp)

                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "sha": data.get("sha"),
                        "commit_message": data.get("commit", {}).get("message"),
                        "author": data.get("commit", {}).get("author", {}).get("name"),
                        "date": data.get("commit", {}).get("author", {}).get("date"),
                        "html_url": data.get("html_url"),
                    }
                else:
                    raise HTTPException(
                        status_code=resp.status_code,
                        detail=f"Failed to retrieve commit '{ref}' from GitHub API (HTTP {resp.status_code})."
                    )
            except httpx.RequestError as exc:
                logger.error(f"HTTP request error fetching commit '{ref}' for {owner}/{repo}: {exc}")
                raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="GitHub API request timed out")

    def _check_rate_limit(self, response: httpx.Response):
        remaining = response.headers.get("X-RateLimit-Remaining")
        if remaining:
            logger.info(f"GitHub API RateLimit Remaining: {remaining}")
