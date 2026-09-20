import os
import hmac
import hashlib
from typing import Optional, Dict, Any, Tuple

class WhatsAppWebhookHandler:
    """
    Handles Meta WhatsApp Webhook verification challenges and HMAC SHA256 signature checks.
    """

    @staticmethod
    def verify_webhook_challenge(
        mode: Optional[str],
        token: Optional[str],
        challenge: Optional[str],
        expected_token: Optional[str] = None
    ) -> Tuple[bool, str]:
        env_token = expected_token or os.getenv("WHATSAPP_VERIFY_TOKEN", "devoncall-verify-token")
        if mode == "subscribe" and token == env_token:
            return True, challenge or ""
        return False, "Verification token mismatch or invalid mode."

    @staticmethod
    def verify_signature(body_bytes: bytes, signature_header: Optional[str], app_secret: Optional[str] = None) -> bool:
        secret = app_secret or os.getenv("WHATSAPP_APP_SECRET", "")
        if not secret:
            # If app secret is not configured, accept in mock/dev mode
            return True

        if not signature_header:
            return False

        # Header format: sha256=hash
        expected_sig = signature_header.replace("sha256=", "").strip()
        computed_sig = hmac.new(secret.encode('utf-8'), body_bytes, hashlib.sha256).hexdigest()

        return hmac.compare_digest(computed_sig, expected_sig)

    @staticmethod
    def parse_incoming_payload(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extracts normalized message data from Meta Cloud API webhook JSON structure.
        """
        try:
            entry = payload.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            messages = value.get("messages", [])

            if not messages:
                return None

            msg = messages[0]
            msg_id = msg.get("id")
            from_phone = msg.get("from")
            msg_type = msg.get("type", "text")

            text = ""
            if msg_type == "text":
                text = msg.get("text", {}).get("body", "")

            return {
                "provider_message_id": msg_id,
                "from_phone": from_phone,
                "message_type": msg_type,
                "text": text
            }
        except Exception:
            return None
