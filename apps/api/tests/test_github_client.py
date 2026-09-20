import pytest
from app.services.integrations.github.mock_provider import MockGitHubProvider

@pytest.mark.asyncio
async def test_mock_github_provider_list_repositories():
    provider = MockGitHubProvider()
    repos = await provider.list_repositories()
    assert len(repos) >= 1
    assert any(r.full_name == "mock-owner/devoncall-demo" for r in repos)

@pytest.mark.asyncio
async def test_mock_github_provider_metadata():
    provider = MockGitHubProvider()
    meta = await provider.get_repository_metadata("mock-owner", "devoncall-demo")
    assert meta.owner == "mock-owner"
    assert meta.repo == "devoncall-demo"
    assert meta.default_branch == "main"
    assert len(meta.commit_sha) > 0

@pytest.mark.asyncio
async def test_mock_github_provider_tree():
    provider = MockGitHubProvider()
    tree = await provider.get_repository_tree("mock-owner", "devoncall-demo", "main")
    assert len(tree) > 0
    paths = [item["path"] for item in tree]
    assert "package.json" in paths
    assert "Dockerfile" in paths
