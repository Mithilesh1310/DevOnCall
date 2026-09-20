import uuid
from datetime import datetime
from typing import List, TYPE_CHECKING, Optional
from sqlalchemy import String, DateTime, Text, ForeignKey, JSON, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.agent_run import AgentRun
    from app.models.incident_investigation import IncidentInvestigation

class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="OPEN")  # OPEN, INVESTIGATING, PROPOSED_FIX, AWAITING_APPROVAL, RESOLVED, IGNORED
    severity: Mapped[str] = mapped_column(String(50), default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL, UNKNOWN
    source: Mapped[str] = mapped_column(String(50), default="manual")  # manual, SENTRY, MOCK_SENTRY, datadog, webhook
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Phase 4 Sentry Metadata Fields
    external_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_issue_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    environment: Mapped[str | None] = mapped_column(String(100), nullable=True)
    release: Mapped[str | None] = mapped_column(String(100), nullable=True)
    commit_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    culprit: Mapped[str | None] = mapped_column(String(255), nullable=True)
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1)
    
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stack_trace: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    normalized_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project: Mapped["Project"] = relationship("Project", back_populates="incidents")
    agent_runs: Mapped[List["AgentRun"]] = relationship("AgentRun", back_populates="incident", cascade="all, delete-orphan")
    investigation: Mapped[Optional["IncidentInvestigation"]] = relationship("IncidentInvestigation", back_populates="incident", uselist=False, cascade="all, delete-orphan")
