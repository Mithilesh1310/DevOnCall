"""
Phase 12: Production Canary & Deployment Database Models.
"""

import uuid
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, DateTime, Text, ForeignKey, JSON, Integer, Float, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project


class ReleaseCandidateModel(Base):
    __tablename__ = "release_candidates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    staging_deployment_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    pr_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="CREATED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    project: Mapped["Project"] = relationship("Project")
    approvals: Mapped[List["ProductionApprovalModel"]] = relationship(
        "ProductionApprovalModel", back_populates="release_candidate", cascade="all, delete-orphan"
    )
    canary_deployments: Mapped[List["CanaryDeploymentModel"]] = relationship(
        "CanaryDeploymentModel", back_populates="release_candidate", cascade="all, delete-orphan"
    )
    production_deployments: Mapped[List["ProductionDeploymentModel"]] = relationship(
        "ProductionDeploymentModel", back_populates="release_candidate", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[List["DeploymentAuditLogModel"]] = relationship(
        "DeploymentAuditLogModel", back_populates="release_candidate", cascade="all, delete-orphan"
    )


class ProductionApprovalModel(Base):
    __tablename__ = "production_approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rc_id: Mapped[str] = mapped_column(String(36), ForeignKey("release_candidates.id", ondelete="CASCADE"), nullable=False)
    approval_type: Mapped[str] = mapped_column(String(50), nullable=False)
    approver_id: Mapped[str] = mapped_column(String(255), nullable=False)
    decision: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confirmation_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    release_candidate: Mapped["ReleaseCandidateModel"] = relationship("ReleaseCandidateModel", back_populates="approvals")


class CanaryDeploymentModel(Base):
    __tablename__ = "canary_deployments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rc_id: Mapped[str] = mapped_column(String(36), ForeignKey("release_candidates.id", ondelete="CASCADE"), nullable=False)
    traffic_percent: Mapped[float] = mapped_column(Float, default=5.0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="STARTING", nullable=False)
    deployment_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    release_candidate: Mapped["ReleaseCandidateModel"] = relationship("ReleaseCandidateModel", back_populates="canary_deployments")
    verifications: Mapped[List["CanaryVerificationRecordModel"]] = relationship(
        "CanaryVerificationRecordModel", back_populates="canary_deployment", cascade="all, delete-orphan"
    )


class CanaryVerificationRecordModel(Base):
    __tablename__ = "canary_verification_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    canary_id: Mapped[str] = mapped_column(String(36), ForeignKey("canary_deployments.id", ondelete="CASCADE"), nullable=False)
    verdict: Mapped[str] = mapped_column(String(50), nullable=False)
    metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    insufficient_data_reasons: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    canary_deployment: Mapped["CanaryDeploymentModel"] = relationship("CanaryDeploymentModel", back_populates="verifications")


class ProductionDeploymentModel(Base):
    __tablename__ = "production_deployments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rc_id: Mapped[str] = mapped_column(String(36), ForeignKey("release_candidates.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="DEPLOYING", nullable=False)
    deployment_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    release_candidate: Mapped["ReleaseCandidateModel"] = relationship("ReleaseCandidateModel", back_populates="production_deployments")
    rollbacks: Mapped[List["RollbackRecordModel"]] = relationship(
        "RollbackRecordModel", back_populates="production_deployment", cascade="all, delete-orphan"
    )


class RollbackRecordModel(Base):
    __tablename__ = "rollback_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    deployment_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("production_deployments.id", ondelete="CASCADE"), nullable=True)
    rc_id: Mapped[str] = mapped_column(String(36), nullable=False)
    target_commit_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="IN_PROGRESS", nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    initiated_by: Mapped[str] = mapped_column(String(255), nullable=False)
    initiated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    production_deployment: Mapped[Optional["ProductionDeploymentModel"]] = relationship("ProductionDeploymentModel", back_populates="rollbacks")


class DeploymentAuditLogModel(Base):
    __tablename__ = "deployment_audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rc_id: Mapped[str] = mapped_column(String(36), ForeignKey("release_candidates.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    release_candidate: Mapped["ReleaseCandidateModel"] = relationship("ReleaseCandidateModel", back_populates="audit_logs")
