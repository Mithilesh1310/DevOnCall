import uuid
from typing import Optional
from app.services.integrations.whatsapp.base import BaseWhatsAppProvider
from app.services.integrations.whatsapp.models import WhatsAppResponse
from app.services.integrations.whatsapp.policies import WhatsAppResponseRedactor

class MockWhatsAppProvider(BaseWhatsAppProvider):
    """
    Deterministic Mock WhatsApp Provider for testing DevOnCall WhatsApp integration offline.
    """

    @property
    def provider_name(self) -> str:
        return "MOCK_WHATSAPP"

    async def send_message(self, recipient_phone_hash: str, text: str, conversation_id: str) -> WhatsAppResponse:
        redacted_text = WhatsAppResponseRedactor.redact(text)
        msg_id = f"mock-wmsg-{uuid.uuid4().hex[:8]}"

        return WhatsAppResponse(
            conversation_id=conversation_id,
            recipient_phone_hash=recipient_phone_hash,
            text=redacted_text,
            provider_message_id=msg_id
        )
