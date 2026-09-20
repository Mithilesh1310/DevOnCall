from typing import Dict, Any, Optional
from app.services.observability.base import BaseObservabilityProvider
from app.services.observability.models import ProductionObservationData, ObservabilitySeverity, ObservabilityStatus, ObservabilityProviderType
from app.services.observability.fingerprint import ObservabilityFingerprinter
from app.services.brain.provenance import BrainSecretRedactor


class MockObservabilityProvider(BaseObservabilityProvider):
    """
    Deterministic Mock Observability Provider for testing production telemetry ingest offline.
    Supports scenarios: NEW_CRITICAL, DUPLICATE, RELEASE_CORRELATED, UNKNOWN_COMMIT, HISTORICAL_MATCH, INVALID_SIGNATURE, SECRET_PAYLOAD.
    """

    @property
    def provider_name(self) -> str:
        return "mock"

    def verify_webhook(self, headers: Dict[str, str], payload_bytes: bytes, secret: Optional[str] = None) -> bool:
        sig = headers.get("x-mock-signature") or headers.get("X-Mock-Signature")
        if sig == "invalid-sig":
            return False
        return True

    def normalize_event(self, payload: Dict[str, Any], project_id: str = "demo-project") -> ProductionObservationData:
        scenario = payload.get("scenario", "NEW_CRITICAL").upper()
        sanitized_payload = BrainSecretRedactor.redact_dict(payload)

        ext_id = str(payload.get("id") or f"mock-evt-{scenario.lower()}")
        msg = str(payload.get("message") or f"Mock {scenario} Production Telemetry Exception")
        sanitized_msg = BrainSecretRedactor.redact_text(msg)

        stack = payload.get("stack_trace") or f"File \"apps/api/app/main.py\", line 42, in process_request\n  raise ValueError('{sanitized_msg}')"
        sanitized_stack = BrainSecretRedactor.redact_text(str(stack))

        service = str(payload.get("service") or "apps/api")
        commit_sha = payload.get("commit_sha")
        release = payload.get("release")

        if scenario == "RELEASE_CORRELATED":
            commit_sha = commit_sha or "a1b2c3d4e5f67890"
            release = release or "v1.4.2"
        elif scenario == "UNKNOWN_COMMIT":
            commit_sha = None
            release = None

        sev = ObservabilitySeverity.CRITICAL if scenario == "NEW_CRITICAL" else ObservabilitySeverity.ERROR

        fp = ObservabilityFingerprinter.generate_fingerprint(
            provider="mock",
            event_type="error",
            service=service,
            message=sanitized_msg,
            stack_frame=sanitized_stack,
            endpoint=payload.get("endpoint") or "/api/v1/checkout"
        )

        return ProductionObservationData(
            project_id=project_id,
            provider=ObservabilityProviderType.MOCK,
            external_event_id=ext_id,
            fingerprint=fp,
            event_type="error",
            severity=sev,
            status=ObservabilityStatus.OPEN,
            environment="PRODUCTION",
            service=service,
            release=release,
            commit_sha=commit_sha,
            message=sanitized_msg,
            stack_trace=sanitized_stack,
            endpoint=payload.get("endpoint") or "/api/v1/checkout",
            request_method=payload.get("request_method") or "POST",
            occurrence_count=int(payload.get("occurrence_count") or 1),
            metadata_payload=sanitized_payload
        )

    def get_event(self, external_event_id: str) -> Optional[ProductionObservationData]:
        return self.normalize_event({"id": external_event_id, "scenario": "NEW_CRITICAL"})

    def health_check(self) -> Dict[str, Any]:
        return {"status": "HEALTHY", "provider": "mock", "mode": "MOCK_DETERMINISTIC"}
