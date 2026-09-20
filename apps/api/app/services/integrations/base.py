from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseIntegrationProvider(ABC):
    """
    Abstract interface for 3rd-party integrations (GitHub, Sentry, Datadog, WhatsApp).
    Ensures provider-specific logic is never hardcoded into core HTTP API routes.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    async def verify_connection(self) -> bool:
        pass

    @abstractmethod
    async def process_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        pass
