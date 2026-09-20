import re
from typing import Dict, Any, Optional

SECRET_PATTERNS = [
    (re.compile(r'(devoncall_sec_[a-zA-Z0-9_-]{16,})', re.IGNORECASE), "[REDACTED_SECRET_KEY]"),
    (re.compile(r'(ghp_[a-zA-Z0-9]{30,})', re.IGNORECASE), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r'(AKIA[0-9A-Z]{16})', re.IGNORECASE), "[REDACTED_AWS_KEY]"),
    (re.compile(r'(sk-[a-zA-Z0-9_-]{10,})', re.IGNORECASE), "[REDACTED_API_KEY]"),
    (re.compile(r'(password|passwd|secret|token|api_key|privkey)=([^&\s]+)', re.IGNORECASE), r"\1=[REDACTED]"),
    (re.compile(r'(postgres|mysql|mongodb)://[^:]+:[^@]+@', re.IGNORECASE), r"\1://[REDACTED_USER]:[REDACTED_PASS]@"),
    (re.compile(r'https?://[^:]+:[^@]+@', re.IGNORECASE), r"https://[REDACTED_AUTH]@"),
]

SECRET_KEY_NAMES = {"password", "passwd", "secret", "token", "api_key", "private_key", "privkey"}


class BrainSecretRedactor:
    """
    Scrubs secrets, tokens, passwords, and private credentials before Brain persistence.
    """

    @staticmethod
    def redact_text(text: Optional[str]) -> str:
        if not text:
            return ""
        result = str(text)
        for pattern, replacement in SECRET_PATTERNS:
            result = pattern.sub(replacement, result)
        return result

    @staticmethod
    def redact_dict(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not data:
            return {}
        cleaned = {}
        for k, v in data.items():
            if k.lower() in SECRET_KEY_NAMES or any(s in k.lower() for s in ["password", "api_key", "token", "secret"]):
                cleaned[k] = "[REDACTED_SECRET]"
            elif isinstance(v, str):
                cleaned[k] = BrainSecretRedactor.redact_text(v)
            elif isinstance(v, dict):
                cleaned[k] = BrainSecretRedactor.redact_dict(v)
            elif isinstance(v, list):
                cleaned[k] = [
                    BrainSecretRedactor.redact_text(item) if isinstance(item, str) else item for item in v
                ]
            else:
                cleaned[k] = v
        return cleaned
