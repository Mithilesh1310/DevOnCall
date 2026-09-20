import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Text, JSON, Integer, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class SandboxRun(Base):
    __tablename__ = "sandbox_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    agent_run_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    workspace_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    
    command_type: Mapped[str] = mapped_column(String(50), nullable=False)  # TEST, BUILD, LINT, TYPECHECK
    runtime: Mapped[str] = mapped_column(String(50), default="python")
    provider_type: Mapped[str] = mapped_column(String(50), default="MOCK_SANDBOX")  # MOCK_SANDBOX, DOCKER_SANDBOX
    status: Mapped[str] = mapped_column(String(50), default="QUEUED")
    
    exit_code: Mapped[int] = mapped_column(Integer, default=-1)
    stdout: Mapped[str] = mapped_column(Text, default="")
    stderr: Mapped[str] = mapped_column(Text, default="")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=120)
    
    resource_limits: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
