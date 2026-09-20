import hmac
import hashlib
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger("devoncall.integrations.sentry.webhook")

def verify_sentry_signature(
    raw_body: bytes,
    signature_header: Optional[str],
    secret: Optional[str] = None
) -> bool:
    """
    Verifies Sentry webhook signature using HMAC SHA256.
    Rejects invalid signatures when SENTRY_WEBHOOK_SECRET is set or supplied.
    """
    webhook_secret = secret or getattr(settings, "SENTRY_WEBHOOK_SECRET", None)

    # In mock/development mode without secret, accept requests but mark as unverified
    if not webhook_secret:
        logger.info("No SENTRY_WEBHOOK_SECRET configured. Webhook running in development/mock verification mode.")
        return True

    if not signature_header:
        logger.warning("Missing Sentry signature header in webhook request.")
        return False

    try:
        expected_sig = hmac.new(
            webhook_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256
        ).hexdigest()

        # Compare signatures in constant time
        is_valid = hmac.compare_digest(expected_sig, signature_header)
        if not is_valid:
            logger.warning("Invalid Sentry webhook signature received.")
        return is_valid
    except Exception as e:
        logger.error(f"Error verifying Sentry webhook signature: {e}")
        return False
