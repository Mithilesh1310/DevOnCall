import os
from app.config import settings
from app.services.integrations.git_base import BaseGitProvider
from app.services.integrations.github.client import GitHubProvider
from app.services.integrations.github.mock_provider import MockGitHubProvider
from app.services.integrations.github.inspector import RepositoryInspector


def get_git_provider(access_token: str | None = None, use_mock: bool = False) -> BaseGitProvider:
    """
    Factory function for obtaining the active Git Provider instance.
    Uses MockGitHubProvider when TEST_MODE or settings.USE_MOCK_GITHUB or use_mock=True.
    Returns GitHubProvider if access_token or token is present or if USE_MOCK_GITHUB is False.
    """
    test_mode = os.getenv("TEST_MODE", "false").lower() in ["true", "1", "yes"]
    use_mock_setting = getattr(settings, "USE_MOCK_GITHUB", False)
    token = access_token or os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PAT") or getattr(settings, "GITHUB_TOKEN", None)

    if use_mock or test_mode or (use_mock_setting and not access_token):
        return MockGitHubProvider()

    return GitHubProvider(access_token=token or "token_placeholder")


__all__ = ["BaseGitProvider", "GitHubProvider", "MockGitHubProvider", "RepositoryInspector", "get_git_provider"]
