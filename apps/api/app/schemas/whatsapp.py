from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AuthorizedDeveloperCreate(BaseModel):
    phone_number: str = Field(..., description="Developer phone number e.g. +14155552671")
    name: str = Field(..., description="Developer full name")
    role: str = Field("DEVELOPER", description="Role e.g. VIEWER, DEVELOPER, APPROVER, ADMIN")
    enabled: bool = True


class AuthorizedDeveloperResponse(BaseModel):
    id: str
    phone_number: str
    identity_hash: str
    name: str
    role: str
    enabled: bool
    created_at: Any


class WhatsAppSimulateRequest(BaseModel):
    sender_phone: str = Field(..., description="Sender phone number e.g. +14155552671")
    raw_text: str = Field(..., description="Command or text message sent by developer")
    use_mock: bool = True


class WhatsAppSimulateResponse(BaseModel):
    success: bool
    conversation_id: Optional[str] = None
    is_authorized: bool
    developer_name: Optional[str] = None
    role: Optional[str] = None
    command_type: str
    response_text: str
    is_redacted: bool
    confirmation_token: Optional[str] = None


class WhatsAppMessageResponse(BaseModel):
    id: str
    direction: str
    sender_phone: str
    recipient_phone: str
    raw_text: str
    command_type: Optional[str] = None
    is_authorized: bool
    is_redacted: bool
    status: str
    created_at: Any


class WhatsAppConversationResponse(BaseModel):
    id: str
    developer_id: str
    developer_name: str
    phone_number: str
    active_project_id: Optional[str] = None
    state: str
    updated_at: Any
    messages: List[WhatsAppMessageResponse] = []


class WhatsAppProviderStatusResponse(BaseModel):
    provider_type: str
    is_configured: bool
    webhook_url: str
    developers_count: int
    active_conversations_count: int
    production_deployments_allowed: bool = False
