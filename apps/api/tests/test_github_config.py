import pytest
from app.config import settings
from app.services.integrations.github import get_git_provider, MockGitHubProvider

def test_github_settings_default_values():
    assert hasattr(settings, "GITHUB_CLIENT_ID")
    assert hasattr(settings, "GITHUB_CLIENT_SECRET")
    assert hasattr(settings, "GITHUB_REDIRECT_URI")
    assert hasattr(settings, "USE_MOCK_GITHUB")
    assert settings.USE_MOCK_GITHUB is True

def test_git_provider_factory_selects_mock():
    provider = get_git_provider()
    assert isinstance(provider, MockGitHubProvider)
    assert provider.provider_name == "mock-github"
