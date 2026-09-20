from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.services.observability.models import ProductionObservationData


class BaseObservabilityProvider(ABC):
    """
    Abstract base class for all production observability providers (Sentry, Generic Webhook, Mock).
    Strictly READ_ONLY telemetry ingestion interface.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name identifier of the provider."""
        pass

    @abstractmethod
    def verify_webhook(self, headers: Dict[str, str], payload_bytes: bytes, secret: Optional[str] = None) -> bool:
        """Verify webhook signature, HMAC token, or authorization headers."""
        pass

    @abstractmethod
    def normalize_event(self, payload: Dict[str, Any], project_id: str = "demo-project") -> ProductionObservationData:
        """Normalize raw provider payload into standardized ProductionObservationData."""
        pass

    @abstractmethod
    def get_event(self, external_event_id: str) -> Optional[ProductionObservationData]:
        """Fetch event metadata by provider external event ID."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Check provider connectivity status."""
        pass
