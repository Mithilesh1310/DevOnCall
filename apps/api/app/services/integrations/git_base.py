from abc import ABC, abstractmethod
from typing import List, Dict, Any
from app.schemas.repository import RepositoryMetadata, GitHubRepoSummary

class BaseGitProvider(ABC):
    """
    Abstract interface boundary for Git host integration providers (GitHub, GitLab, Bitbucket).
    Decouples core DevOnCall logic from vendor-specific API structures.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    async def is_authenticated(self) -> bool:
        pass

    @abstractmethod
    async def list_repositories(self) -> List[GitHubRepoSummary]:
        pass

    @abstractmethod
    async def get_repository_metadata(self, owner: str, repo: str) -> RepositoryMetadata:
        pass

    @abstractmethod
    async def get_repository_tree(self, owner: str, repo: str, branch: str) -> List[Dict[str, Any]]:
        """
        Fetch flat git tree items (list of path, type, size, sha).
        """
        pass
