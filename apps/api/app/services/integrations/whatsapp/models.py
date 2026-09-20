import hashlib
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone

class WhatsAppRole(str, Enum):
    VIEWER = "VIEWER"
    DEVELOPER = "DEVELOPER"
    APPROVER = "APPROVER"
    ADMIN = "ADMIN"

class WhatsAppMessageStatus(str, Enum):
    RECEIVED = "RECEIVED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"

class WhatsAppConversationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    CLOSED = "CLOSED"

class CommandType(str, Enum):
    HELP = "HELP"
    STATUS = "STATUS"
    INCIDENTS = "INCIDENTS"
    INCIDENTS_CRITICAL = "INCIDENTS_CRITICAL"
    INCIDENTS_OPEN = "INCIDENTS_OPEN"
    INCIDENT = "INCIDENT"
    INVESTIGATE = "INVESTIGATE"
    DETAILS = "DETAILS"
    FIX = "FIX"
    CONFIRM = "CONFIRM"
    CANCEL = "CANCEL"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    VALIDATION = "VALIDATION"
    STAGING = "STAGING"
    STAGING_STATUS = "STAGING_STATUS"
    BRAIN = "BRAIN"
    BRAIN_SUMMARY = "BRAIN_SUMMARY"
    BRAIN_INCIDENTS = "BRAIN_INCIDENTS"
    BRAIN_SEARCH = "BRAIN_SEARCH"
    RELEASES = "RELEASES"
    CANARY = "CANARY"
    APPROVE_CANARY = "APPROVE_CANARY"
    APPROVE_PRODUCTION = "APPROVE_PRODUCTION"
    REJECT_RELEASE = "REJECT_RELEASE"
    APPROVE_ROLLBACK = "APPROVE_ROLLBACK"
    STOP = "STOP"
    PROJECT = "PROJECT"
    WHOAMI = "WHOAMI"
    UNKNOWN = "UNKNOWN"



class WhatsAppMessage(BaseModel):
    id: str
    provider_message_id: str
    conversation_id: str
    sender_id: str
    sender_phone_hash: str
    message_type: str = "text"
    text: str
    received_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    processed_at: Optional[str] = None
    status: WhatsAppMessageStatus = WhatsAppMessageStatus.RECEIVED
    error_message: Optional[str] = None

class WhatsAppConversation(BaseModel):
    id: str
    sender_identity_hash: str
    project_id: str
    active_agent_run_id: Optional[str] = None
    last_message_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: WhatsAppConversationStatus = WhatsAppConversationStatus.ACTIVE

class AuthorizedDeveloper(BaseModel):
    id: str
    identity_hash: str
    name: str
    phone_number_masked: str
    project_id: str
    role: WhatsAppRole = WhatsAppRole.DEVELOPER
    enabled: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @staticmethod
    def hash_phone(phone_number: str) -> str:
        clean = "".join(c for c in phone_number if c.isdigit())
        return hashlib.sha256(clean.encode('utf-8')).hexdigest()

class ConfirmationToken(BaseModel):
    id: str
    token: str
    incident_id: str
    agent_run_id: Optional[str] = None
    action: str  # FIX, APPROVE, REJECT
    identity_hash: str
    expires_at: str
    used: bool = False

class ParsedCommand(BaseModel):
    command_type: CommandType
    incident_id: Optional[str] = None
    target_id: Optional[str] = None
    page: int = 1
    raw_text: str
    token: Optional[str] = None

class WhatsAppResponse(BaseModel):
    conversation_id: str
    recipient_phone_hash: str
    text: str
    provider_message_id: Optional[str] = None
    sent_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
