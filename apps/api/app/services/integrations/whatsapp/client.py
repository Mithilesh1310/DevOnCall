import os
import uuid
import httpx
from typing import Optional
from app.services.integrations.whatsapp.base import BaseWhatsAppProvider
from app.services.integrations.whatsapp.models import WhatsAppResponse
from app.services.integrations.whatsapp.policies import WhatsAppResponseRedactor

class WhatsAppCloudClient(BaseWhatsAppProvider):
    """
    Official WhatsApp Cloud API Integration Boundary.
    Communicates with Meta Business API endpoints when credentials are configured.
    """

    def __init__(self, access_token: Optional[str] = None, phone_number_id: Optional[str] = None):
        self.access_token = access_token or os.getenv("WHATSAPP_ACCESS_TOKEN", "")
        self.phone_number_id = phone_number_id or os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")

    @property
    def provider_name(self) -> str:
        return "WHATSAPP_CLOUD_API"

    @property
    def is_configured(self) -> bool:
        return bool(self.access_token and self.phone_number_id)

    async def send_message(self, recipient_phone_hash: str, text: str, conversation_id: str) -> WhatsAppResponse:
        redacted_text = WhatsAppResponseRedactor.redact(text)

        if not self.is_configured:
            # Report REAL WHATSAPP RUNTIME = BLOCKED cleanly
            return WhatsAppResponse(
                conversation_id=conversation_id,
                recipient_phone_hash=recipient_phone_hash,
                text=f"[REAL WHATSAPP RUNTIME = BLOCKED - Credentials Not Configured] {redacted_text}",
                provider_message_id=f"blocked-{uuid.uuid4().hex[:8]}"
            )

        url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_phone_hash,
            "type": "text",
            "text": {"body": redacted_text}
        }

        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(url, json=payload, headers=headers, timeout=10.0)
                if res.status_code == 200:
                    data = res.json()
                    msg_id = data.get("messages", [{}])[0].get("id", uuid.uuid4().hex)
                    return WhatsAppResponse(
                        conversation_id=conversation_id,
                        recipient_phone_hash=recipient_phone_hash,
                        text=redacted_text,
                        provider_message_id=msg_id
                    )
                else:
                    return WhatsAppResponse(
                        conversation_id=conversation_id,
                        recipient_phone_hash=recipient_phone_hash,
                        text=f"[WHATSAPP_SEND_FAILED - HTTP {res.status_code}] {redacted_text}",
                        provider_message_id=f"failed-{uuid.uuid4().hex[:8]}"
                    )
        except Exception as ex:
            return WhatsAppResponse(
                conversation_id=conversation_id,
                recipient_phone_hash=recipient_phone_hash,
                text=f"[WHATSAPP_SEND_ERROR - {str(ex)}] {redacted_text}",
                provider_message_id=f"error-{uuid.uuid4().hex[:8]}"
            )
