from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class FrameworkDetection(BaseModel):
    name: str
    type: Literal["framework", "runtime", "language", "package_manager"]
    status: Literal["DETECTED", "INFERRED"]
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: List[str]

class RepositoryTreeNode(BaseModel):
    path: str
    name: str
    type: Literal["file", "directory"]
    size: Optional[int] = None
    children: Optional[List["RepositoryTreeNode"]] = None

class RepositoryMetadata(BaseModel):
    owner: str
    repo: str
    default_branch: str = "main"
    commit_sha: str
    html_url: str
    is_private: bool = False

class RepositorySnapshot(BaseModel):
    owner: str
    repo: str
    default_branch: str
    commit_sha: str
    url: str
    total_files: int
    total_directories: int
    detected_languages: List[str]
    detections: List[FrameworkDetection]
    important_files: List[str]
    source_directories: List[str]
    test_directories: List[str]
    configuration_files: List[str]
    tree: List[RepositoryTreeNode]
    inspected_at: datetime

class GitHubStatusResponse(BaseModel):
    provider_type: Literal["mock", "oauth"]
    mock_enabled: bool
    client_id_configured: bool
    status: str

class GitHubRepoSummary(BaseModel):
    id: str
    owner: str
    name: str
    full_name: str
    default_branch: str
    html_url: str
    is_private: bool
    description: Optional[str] = None

class GitHubConnectRequest(BaseModel):
    github_owner: str
    github_repo: str
    default_branch: Optional[str] = "main"
