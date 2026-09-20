from typing import List
from fastapi import APIRouter
from app.config import settings
from app.services.integrations.github import get_git_provider
from app.schemas.repository import GitHubStatusResponse, GitHubRepoSummary

router = APIRouter()

@router.get("/status", response_model=GitHubStatusResponse)
async def get_github_integration_status():
    provider = get_git_provider()
    provider_type = "mock" if provider.provider_name == "mock-github" else "oauth"
    client_id_set = bool(settings.GITHUB_CLIENT_ID)
    
    status_msg = (
        "Development Mock Provider Active" if provider_type == "mock" 
        else "GitHub OAuth Production Provider Ready"
    )

    return GitHubStatusResponse(
        provider_type=provider_type,
        mock_enabled=settings.USE_MOCK_GITHUB,
        client_id_configured=client_id_set,
        status=status_msg
    )

@router.get("/repos", response_model=List[GitHubRepoSummary])
async def list_github_repositories():
    provider = get_git_provider()
    repos = await provider.list_repositories()
    return repos
