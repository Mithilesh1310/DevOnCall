import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, DateTime, Text, ForeignKey, JSON, Float, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.incident import Incident

class IncidentInvestigation(Base):
    __tablename__ = "incident_investigations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id: Mapped[str] = mapped_column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    status: Mapped[str] = mapped_column(String(50), default="PENDING")  # PENDING, INVESTIGATING, COMPLETED, FAILED
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    
    hypothesis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    evidence: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    relevant_files: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    relevant_stack_frames: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    repository_matches: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    suspected_locations: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    proposed_fix: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    recommended_next_action: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    incident: Mapped["Incident"] = relationship("Incident", back_populates="investigation")
