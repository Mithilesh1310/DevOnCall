from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict
from app.schemas.repository import RepositorySnapshot

class ProjectBase(BaseModel):
    name: str
    repo_url: Optional[str] = None
    default_branch: str = "main"

class ProjectCreate(ProjectBase):
    github_owner: Optional[str] = None
    github_repo: Optional[str] = None

class ProjectResponse(ProjectBase):
    id: str
    github_owner: Optional[str] = None
    github_repo: Optional[str] = None
    github_url: Optional[str] = None
    last_indexed_commit_sha: Optional[str] = None
    last_indexed_at: Optional[datetime] = None
    repository_snapshot: Optional[RepositorySnapshot] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
