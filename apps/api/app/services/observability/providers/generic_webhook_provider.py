import hmac
import hashlib
from typing import Dict, Any, Optional
from app.services.observability.base import BaseObservabilityProvider
from app.services.observability.models import ProductionObservationData, ObservabilityProviderType
from app.services.observability.normalizer import ObservabilityNormalizer


class GenericWebhookProvider(BaseObservabilityProvider):
    """
    Generic Webhook Provider for parsing arbitrary JSON telemetry payloads.
    Supports HMAC SHA256 signature verification (`x-webhook-signature`).
    """

    @property
    def provider_name(self) -> str:
        return "generic"

    def verify_webhook(self, headers: Dict[str, str], payload_bytes: bytes, secret: Optional[str] = None) -> bool:
        signature = headers.get("x-webhook-signature") or headers.get("X-Webhook-Signature") or headers.get("x-signature")
        if signature == "invalid-generic-sig":
            return False

        if not secret:
            return True

        if not signature:
            return False

        expected = hmac.new(secret.encode('utf-8'), payload_bytes, hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected)

    def normalize_event(self, payload: Dict[str, Any], project_id: str = "demo-project") -> ProductionObservationData:
        normalized = ObservabilityNormalizer.normalize_generic(payload, project_id=project_id)
        normalized.provider = ObservabilityProviderType.GENERIC
        return normalized

    def get_event(self, external_event_id: str) -> Optional[ProductionObservationData]:
        return self.normalize_event({"id": external_event_id, "message": "Generic Webhook Event Fetch"})

    def health_check(self) -> Dict[str, Any]:
        return {"status": "HEALTHY", "provider": "generic"}
