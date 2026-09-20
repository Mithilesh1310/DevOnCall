import uuid
from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, DateTime, Text, ForeignKey, JSON, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.agent_run import AgentRun


class StagingDeploymentModel(Base):
    __tablename__ = "staging_deployments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    agent_run_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True)
    workspace_id: Mapped[str] = mapped_column(String(255), nullable=False)
    branch: Mapped[str] = mapped_column(String(255), nullable=False)
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    environment: Mapped[str] = mapped_column(String(50), default="STAGING", nullable=False)
    provider: Mapped[str] = mapped_column(String(50), default="MOCK_STAGING", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="QUEUED", nullable=False)
    deployment_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    health_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    error_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    project: Mapped["Project"] = relationship("Project")
    agent_run: Mapped[Optional["AgentRun"]] = relationship("AgentRun")
    checks: Mapped[List["StagingCheckResultModel"]] = relationship(
        "StagingCheckResultModel", back_populates="deployment", cascade="all, delete-orphan"
    )


class StagingCheckResultModel(Base):
    __tablename__ = "staging_check_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    deployment_id: Mapped[str] = mapped_column(String(36), ForeignKey("staging_deployments.id", ondelete="CASCADE"), nullable=False)
    check_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PASS", nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    deployment: Mapped["StagingDeploymentModel"] = relationship("StagingDeploymentModel", back_populates="checks")
