import pytest
from app.services.integrations.sentry import SentryNormalizer, MockSentryProvider

def test_sentry_normalizer_redaction():
    raw_payload = {
        "event": {
            "event_id": "evt-123",
            "request": {
                "headers": {
                    "Authorization": "Bearer secret_jwt_token_12345",
                    "Cookie": "session_id=secret_cookie",
                    "User-Agent": "Mozilla/5.0"
                },
                "data": {
                    "password": "super_secret_password",
                    "user_email": "user@example.com"
                }
            }
        }
    }

    normalized = SentryNormalizer.normalize_event(raw_payload, is_mock=True)
    assert normalized.event_id == "evt-123"
    assert normalized.is_mock is True
    assert normalized.source == "MOCK_SENTRY"

    # Verify redaction of sensitive keys
    sanitized = SentryNormalizer.redact_dict(raw_payload)
    headers = sanitized["event"]["request"]["headers"]
    data = sanitized["event"]["request"]["data"]

    assert headers["Authorization"] == "[REDACTED]"
    assert headers["Cookie"] == "[REDACTED]"
    assert headers["User-Agent"] == "Mozilla/5.0"
    assert data["password"] == "[REDACTED]"
    assert data["user_email"] == "user@example.com"

def test_sentry_normalizer_mock_provider():
    mock_payload = MockSentryProvider.generate_mock_payload("python_attribute_error")
    normalized = SentryNormalizer.normalize_event(mock_payload, is_mock=True)

    assert normalized.error_type == "AttributeError"
    assert "NoneType" in normalized.error_message
    assert len(normalized.stack_trace) == 2
    assert normalized.stack_trace[0].file == "app/main.py"
    assert normalized.stack_trace[1].file == "app/services/user.py"
