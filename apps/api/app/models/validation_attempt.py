import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Text, JSON, Integer, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class ValidationAttempt(Base):
    __tablename__ = "validation_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_run_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    sandbox_run_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    iteration: Mapped[int] = mapped_column(Integer, default=1)

    command_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # PASSED, FAILED, TIMED_OUT, BLOCKED, ERROR
    failure_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    summary: Mapped[str] = mapped_column(Text, default="")
    diagnostic_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    action_taken: Mapped[str] = mapped_column(String(50), default="CONTINUE")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
