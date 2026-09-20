import uuid
from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, DateTime, Text, Boolean, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project


class AuthorizedDeveloperModel(Base):
    __tablename__ = "authorized_developers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    phone_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    identity_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="DEVELOPER")  # VIEWER, DEVELOPER, APPROVER, ADMIN
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    conversations: Mapped[List["WhatsAppConversationModel"]] = relationship(
        "WhatsAppConversationModel", back_populates="developer", cascade="all, delete-orphan"
    )
    tokens: Mapped[List["ConfirmationTokenModel"]] = relationship(
        "ConfirmationTokenModel", back_populates="developer", cascade="all, delete-orphan"
    )


class WhatsAppConversationModel(Base):
    __tablename__ = "whatsapp_conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    developer_id: Mapped[str] = mapped_column(String(36), ForeignKey("authorized_developers.id", ondelete="CASCADE"), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(50), nullable=False)
    active_project_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    state: Mapped[str] = mapped_column(String(50), default="IDLE")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    developer: Mapped["AuthorizedDeveloperModel"] = relationship("AuthorizedDeveloperModel", back_populates="conversations")
    project: Mapped[Optional["Project"]] = relationship("Project")
    messages: Mapped[List["WhatsAppMessageModel"]] = relationship(
        "WhatsAppMessageModel", back_populates="conversation", cascade="all, delete-orphan"
    )


class WhatsAppMessageModel(Base):
    __tablename__ = "whatsapp_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("whatsapp_conversations.id", ondelete="SET NULL"), nullable=True)
    provider_message_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)  # INBOUND, OUTBOUND
    sender_phone: Mapped[str] = mapped_column(String(50), nullable=False)
    recipient_phone: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_command: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    command_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_authorized: Mapped[bool] = mapped_column(Boolean, default=False)
    is_redacted: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(50), default="SENT")  # RECEIVED, SENT, FAILED

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped[Optional["WhatsAppConversationModel"]] = relationship("WhatsAppConversationModel", back_populates="messages")


class ConfirmationTokenModel(Base):
    __tablename__ = "confirmation_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    token: Mapped[str] = mapped_column(String(16), unique=True, index=True, nullable=False)
    developer_id: Mapped[str] = mapped_column(String(36), ForeignKey("authorized_developers.id", ondelete="CASCADE"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    developer: Mapped["AuthorizedDeveloperModel"] = relationship("AuthorizedDeveloperModel", back_populates="tokens")
