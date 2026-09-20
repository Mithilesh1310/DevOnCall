import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, JSON, Text
from app.db.base import Base


class ProductionObservationModel(Base):
    """
    SQLAlchemy ORM model for production telemetry observations.
    Table: production_observations
    Indexed by: project_id, provider, fingerprint, severity, status, service, commit_sha, first_seen_at, last_seen_at.
    """
    __tablename__ = "production_observations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(100), nullable=False, index=True)
    provider = Column(String(50), nullable=False, index=True, default="generic")
    external_event_id = Column(String(255), nullable=False)
    fingerprint = Column(String(64), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, default="error")
    severity = Column(String(20), nullable=False, index=True, default="ERROR")
    status = Column(String(20), nullable=False, index=True, default="OPEN")
    environment = Column(String(50), nullable=False, default="PRODUCTION")
    service = Column(String(100), nullable=False, index=True, default="unknown-service")
    release = Column(String(100), nullable=True)
    commit_sha = Column(String(64), nullable=True, index=True)
    message = Column(Text, nullable=False)
    stack_trace = Column(Text, nullable=True)
    endpoint = Column(String(255), nullable=True)
    request_method = Column(String(10), nullable=True)
    source_url = Column(String(500), nullable=True)
    first_seen_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    last_seen_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    occurrence_count = Column(Integer, default=1, nullable=False)
    metadata_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
