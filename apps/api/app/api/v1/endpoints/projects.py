from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import get_db
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectResponse
from app.schemas.repository import GitHubConnectRequest, RepositorySnapshot
from app.services.integrations.github import get_git_provider, RepositoryInspector

router = APIRouter()

@router.get("", response_model=List[ProjectResponse])
async def list_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).order_by(Project.created_at.desc()))
    projects = result.scalars().all()
    return projects

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(project_in: ProjectCreate, db: AsyncSession = Depends(get_db)):
    github_url = None
    if project_in.github_owner and project_in.github_repo:
        github_url = f"https://github.com/{project_in.github_owner}/{project_in.github_repo}"

    project = Project(
        name=project_in.name,
        repo_url=project_in.repo_url or github_url,
        default_branch=project_in.default_branch,
        github_owner=project_in.github_owner,
        github_repo=project_in.github_repo,
        github_url=github_url
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project

@router.post("/{project_id}/github/connect", response_model=ProjectResponse)
async def connect_github_repository(
    project_id: str,
    connect_in: GitHubConnectRequest,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    project.github_owner = connect_in.github_owner
    project.github_repo = connect_in.github_repo
    project.github_url = f"https://github.com/{connect_in.github_owner}/{connect_in.github_repo}"
    if connect_in.default_branch:
        project.default_branch = connect_in.default_branch

    await db.commit()
    await db.refresh(project)
    return project

@router.post("/{project_id}/github/inspect", response_model=ProjectResponse)
async def inspect_repository(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if not project.github_owner or not project.github_repo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project does not have a connected GitHub repository. Call /github/connect first."
        )

    provider = get_git_provider()
    
    # 1. Fetch metadata & tree from provider
    metadata = await provider.get_repository_metadata(project.github_owner, project.github_repo)
    raw_tree = await provider.get_repository_tree(project.github_owner, project.github_repo, metadata.default_branch)

    # 2. Run deterministic Repository Inspector
    snapshot = RepositoryInspector.inspect(metadata, raw_tree)

    # 3. Save snapshot to project record
    project.default_branch = snapshot.default_branch
    project.last_indexed_commit_sha = snapshot.commit_sha
    project.last_indexed_at = datetime.now(timezone.utc)
    project.repository_snapshot = snapshot.model_dump(mode="json")

    await db.commit()

    await db.refresh(project)
    return project

@router.get("/{project_id}/snapshot", response_model=RepositorySnapshot)
async def get_project_snapshot(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if not project.repository_snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository snapshot has not been created yet for this project."
        )

    return project.repository_snapshot
