import re
from urllib.parse import urlparse
from typing import List, Tuple, Set
from app.services.browser.models import SelectorStrategy

FORBIDDEN_SCHEMES: Set[str] = {"file", "chrome", "data", "devtools", "javascript", "about"}

FORBIDDEN_HOSTS: Set[str] = {
    "169.254.169.254",
    "metadata.google.internal",
    "metadata.aws.internal",
    "169.254.169.254.ip.linodeusercontent.com"
}

FORBIDDEN_PORTS: Set[int] = {22, 23, 25, 53, 3306, 5432, 6379, 27017, 11211}

DEFAULT_ALLOWED_BASE_URLS: List[str] = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://web-under-test:3000"
]

REDACTION_PATTERNS = [
    (re.compile(r'(password|passwd|secret|token|api_key|auth|cookie)=([^&\s]+)', re.IGNORECASE), r'\1=[REDACTED]'),
    (re.compile(r'(Authorization:\s*Bearer\s+|Bearer\s+)([^\s]+)', re.IGNORECASE), r'\1[REDACTED]'),
    (re.compile(r'"(password|token|secret|api_key)":\s*"([^"]+)"', re.IGNORECASE), r'"\1": "[REDACTED]"')
]


class BrowserSecurityPolicy:
    """
    Strict security policy governing browser navigation, URL validation, and selector strategies.
    Prevent SSFR, internal network scanning, host file access, and credential leakage.
    """

    def __init__(self, allowed_base_urls: List[str] | None = None):
        self.allowed_base_urls = allowed_base_urls if allowed_base_urls is not None else DEFAULT_ALLOWED_BASE_URLS

    def validate_url(self, target_url: str) -> Tuple[bool, str]:
        if not target_url:
            return False, "Target URL cannot be empty."

        parsed = urlparse(target_url)

        # 1. Scheme Check
        if parsed.scheme.lower() in FORBIDDEN_SCHEMES:
            return False, f"Forbidden URL scheme '{parsed.scheme}:'."

        if parsed.scheme.lower() not in {"http", "https"}:
            return False, f"Only HTTP/HTTPS protocols allowed. Received: '{parsed.scheme}:'."

        # 2. Host Metadata & Cloud Metadata Check
        hostname = (parsed.hostname or "").lower()
        if hostname in FORBIDDEN_HOSTS:
            return False, f"Access to cloud metadata or internal host '{hostname}' is strictly forbidden."

        # 3. Forbidden Internal Port Check
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if port in FORBIDDEN_PORTS:
            return False, f"Access to forbidden infrastructure port {port} is denied."

        # 4. Base URL Allowlist Verification
        matched = False
        for allowed_base in self.allowed_base_urls:
            allowed_parsed = urlparse(allowed_base)
            if (
                parsed.scheme.lower() == allowed_parsed.scheme.lower()
                and (parsed.hostname or "").lower() == (allowed_parsed.hostname or "").lower()
                and (parsed.port or (443 if parsed.scheme == "https" else 80)) == (allowed_parsed.port or (443 if allowed_parsed.scheme == "https" else 80))
            ):
                matched = True
                break

        if not matched:
            return False, f"URL '{target_url}' is not in allowed base URLs allowlist: {self.allowed_base_urls}"

        return True, "URL validated successfully."

    def determine_selector_strategy(self, selector: str | None) -> SelectorStrategy:
        if not selector:
            return SelectorStrategy.STABLE_CSS

        if "data-testid" in selector or "data-test" in selector or "data-qa" in selector:
            return SelectorStrategy.DATA_TESTID
        elif "role=" in selector or "aria-" in selector:
            return SelectorStrategy.ACCESSIBLE_ROLE
        elif "label" in selector or "name=" in selector:
            return SelectorStrategy.LABEL
        elif ":nth-child" in selector or ":nth-of-type" in selector or re.search(r'\.[a-zA-Z0-9]{8,}', selector):
            return SelectorStrategy.FRAGILE_CSS
        else:
            return SelectorStrategy.STABLE_CSS

class CredentialRedactor:
    """
    Utility class to redact credentials, secrets, cookies, tokens from strings, logs, and outputs.
    """

    @staticmethod
    def redact(text: str | None) -> str:
        if not text:
            return ""
        result = str(text)
        for pattern, replacement in REDACTION_PATTERNS:
            result = pattern.sub(replacement, result)
        return result
