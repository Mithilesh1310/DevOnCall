import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, DateTime, Text, JSON, Integer, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class BrowserRun(Base):
    __tablename__ = "browser_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    agent_run_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    workspace_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)

    scenario_id: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(50), default="MOCK_BROWSER")  # MOCK_BROWSER, PLAYWRIGHT_BROWSER
    status: Mapped[str] = mapped_column(String(50), default="QUEUED")  # QUEUED, RUNNING, PASSED, FAILED, TIMED_OUT, BLOCKED, ERROR

    base_url: Mapped[str] = mapped_column(String(255), nullable=False)
    current_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    step_count: Mapped[int] = mapped_column(Integer, default=0)
    passed_steps: Mapped[int] = mapped_column(Integer, default=0)
    failed_steps: Mapped[int] = mapped_column(Integer, default=0)

    error_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    suspected_file: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    artifact_paths: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    console_errors: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    network_errors: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BrowserStepResultModel(Base):
    __tablename__ = "browser_step_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    browser_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("browser_runs.id"), index=True, nullable=False)

    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    selector: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    selector_strategy: Mapped[str] = mapped_column(String(50), default="STABLE_CSS")
    status: Mapped[str] = mapped_column(String(50), default="PASSED")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)

    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    screenshot_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    observed_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
