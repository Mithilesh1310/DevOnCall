from abc import ABC, abstractmethod
from typing import Optional, List
from app.services.integrations.whatsapp.models import WhatsAppResponse, WhatsAppMessage

class BaseWhatsAppProvider(ABC):
    """
    Abstract Base Class for WhatsApp Integration Providers.
    Supports official Cloud API provider and Mock provider.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns MOCK_WHATSAPP or WHATSAPP_CLOUD_API"""
        pass

    @abstractmethod
    async def send_message(self, recipient_phone_hash: str, text: str, conversation_id: str) -> WhatsAppResponse:
        """Sends a text message to recipient."""
        pass
