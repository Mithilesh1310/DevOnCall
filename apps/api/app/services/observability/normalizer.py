from typing import Dict, Any, Optional
from app.services.brain.provenance import BrainSecretRedactor
from app.services.observability.models import ProductionObservationData, ObservabilitySeverity, ObservabilityStatus, ObservabilityProviderType
from app.services.observability.severity import ObservabilitySeverityClassifier
from app.services.observability.fingerprint import ObservabilityFingerprinter


class ObservabilityNormalizer:
    """
    Normalizes provider-specific payloads (Sentry, Generic JSON, Mock) into standardized
    ProductionObservationData while scrubbing secret credentials.
    """

    @staticmethod
    def sanitize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Scrubs passwords, tokens, API keys, DSNs, and secret keys."""
        return BrainSecretRedactor.redact_dict(payload)

    @staticmethod
    def normalize_generic(payload: Dict[str, Any], project_id: str = "demo-project") -> ProductionObservationData:
        sanitized = ObservabilityNormalizer.sanitize_payload(payload)

        ext_id = str(sanitized.get("id") or sanitized.get("external_id") or sanitized.get("event_id") or "evt-gen-101")
        msg = str(sanitized.get("message") or sanitized.get("title") or "Generic Production Observation")
        sanitized_msg = BrainSecretRedactor.redact_text(msg)

        stack = sanitized.get("stack_trace") or sanitized.get("culprit")
        sanitized_stack = BrainSecretRedactor.redact_text(str(stack)) if stack else None

        sev_str = str(sanitized.get("severity") or sanitized.get("level") or "ERROR")
        severity = ObservabilitySeverityClassifier.classify(sev_str)

        service = str(sanitized.get("service") or sanitized.get("app") or "apps/api")
        endpoint = sanitized.get("endpoint") or sanitized.get("path")
        request_method = sanitized.get("request_method") or sanitized.get("method")
        release = sanitized.get("release") or sanitized.get("version")
        commit_sha = sanitized.get("commit_sha") or sanitized.get("commit")

        fp = ObservabilityFingerprinter.generate_fingerprint(
            provider="generic",
            event_type="error",
            service=service,
            message=sanitized_msg,
            stack_frame=sanitized_stack,
            endpoint=endpoint
        )

        return ProductionObservationData(
            project_id=project_id,
            provider=ObservabilityProviderType.GENERIC,
            external_event_id=ext_id,
            fingerprint=fp,
            event_type=str(sanitized.get("event_type") or "error"),
            severity=severity,
            status=ObservabilityStatus.OPEN,
            environment="PRODUCTION",
            service=service,
            release=release,
            commit_sha=commit_sha,
            message=sanitized_msg,
            stack_trace=sanitized_stack,
            endpoint=endpoint,
            request_method=request_method,
            source_url=sanitized.get("source_url"),
            occurrence_count=int(sanitized.get("occurrence_count") or 1),
            metadata_payload=sanitized
        )
