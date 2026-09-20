import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, DateTime, Text, ForeignKey, JSON, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.incident import Incident
    from app.models.project import Project

class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    user_task: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PENDING")  # PENDING, RUNNING, WAITING, AWAITING_APPROVAL, COMPLETED, FAILED, CANCELLED
    current_goal: Mapped[str | None] = mapped_column(String(512), nullable=True)
    current_step: Mapped[int] = mapped_column(Integer, default=0)
    iteration_count: Mapped[int] = mapped_column(Integer, default=0)
    
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_metadata: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    logs: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    
    # Phase 3 Workspace & PR Tracking Fields
    workspace_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    agent_branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    base_commit_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    change_plan: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    diff_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    pull_request_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    pull_request_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    incident: Mapped["Incident | None"] = relationship("Incident", back_populates="agent_runs")
    project: Mapped["Project"] = relationship("Project")
