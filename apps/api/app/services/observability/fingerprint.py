import hashlib
import re
from typing import Optional


class ObservabilityFingerprinter:
    """
    Generates deterministic, stable event fingerprints for production observations.
    Excludes volatile fields like timestamps, line numbers variations, and memory addresses
    to ensure identical incidents deduplicate into the same record.
    """

    @staticmethod
    def generate_fingerprint(
        provider: str,
        event_type: str,
        service: str,
        message: str,
        stack_frame: Optional[str] = None,
        endpoint: Optional[str] = None
    ) -> str:
        # Clean message from volatile hex addresses, numbers, timestamps
        norm_msg = message.lower().strip()
        norm_msg = re.sub(r'0x[0-9a-fA-F]+', '', norm_msg)
        norm_msg = re.sub(r'\b\d{4}-\d{2}-\d{2}[t\s]\d{2}:\d{2}:\d{2}(\.\d+)?\b', '', norm_msg, flags=re.IGNORECASE)
        norm_msg = re.sub(r'\b(frame|line|at)\s+\d+\b', r'\1', norm_msg, flags=re.IGNORECASE)
        norm_msg = re.sub(r'\b\d+\b', '', norm_msg)
        norm_msg = re.sub(r'\s+', ' ', norm_msg).strip()

        norm_service = (service or "unknown-service").lower().strip()
        norm_provider = (provider or "generic").lower().strip()
        norm_event_type = (event_type or "error").lower().strip()
        norm_endpoint = (endpoint or "").lower().strip()
        norm_frame = (stack_frame or "").lower().strip()

        composite_string = f"{norm_provider}:{norm_event_type}:{norm_service}:{norm_msg}:{norm_frame}:{norm_endpoint}"
        return hashlib.sha256(composite_string.encode('utf-8')).hexdigest()[:32]
