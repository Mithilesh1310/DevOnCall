import pytest
from httpx import AsyncClient

from app.services.observability.security import ProductionSafetyPolicy, ForbiddenProductionOperation
from app.services.observability.providers.sentry_provider import SentryObservabilityProvider
from app.services.observability.providers.generic_webhook_provider import GenericWebhookProvider
from app.services.observability.normalizer import ObservabilityNormalizer
from app.services.agent.tools.observability_tools import (
    ProductionIncidentSearchTool,
    ProductionIncidentDetailsTool,
    ProductionIncidentCorrelateTool,
)
from app.services.agent.policies import ToolPermission


def test_production_safety_policy_allowed_operations():
    """Verify read-only telemetry operations are permitted."""
    allowed_ops = [
        "RECEIVE_TELEMETRY",
        "INSPECT_INCIDENT",
        "CORRELATE_COMMIT",
        "INSPECT_REPOSITORY",
        "QUERY_PROJECT_BRAIN",
        "INVESTIGATE_ROOT_CAUSE",
        "PROPOSE_REMEDIATION",
        "CREATE_PHASE3_WORKSPACE",
        "RUN_SANDBOX_VALIDATION",
        "RUN_BROWSER_VERIFICATION",
        "DEPLOY_TO_STAGING",
        "REQUEST_HUMAN_APPROVAL",
    ]
    for op in allowed_ops:
        is_ok, reason = ProductionSafetyPolicy.validate_action(op, environment="PRODUCTION")
        assert is_ok is True
        assert reason == "ALLOWED"


def test_production_safety_policy_forbidden_operations():
    """Verify forbidden production operations are hard rejected."""
    forbidden = [
        ForbiddenProductionOperation.PRODUCTION_SHELL,
        ForbiddenProductionOperation.PRODUCTION_FS_WRITE,
        ForbiddenProductionOperation.PRODUCTION_DB_WRITE,
        ForbiddenProductionOperation.PRODUCTION_RESTART,
        ForbiddenProductionOperation.PRODUCTION_DEPLOY,
        ForbiddenProductionOperation.PRODUCTION_ROLLBACK,
        ForbiddenProductionOperation.PRODUCTION_ENV_MODIFY,
        ForbiddenProductionOperation.PRODUCTION_CREDENTIAL_ACCESS,
    ]
    for op in forbidden:
        is_ok, reason = ProductionSafetyPolicy.validate_action(op.value, environment="PRODUCTION")
        assert is_ok is False
        assert "SECURITY_POLICY_VIOLATION" in reason


def test_sentry_webhook_signature_verification():
    """Verify Sentry HMAC webhook signature validation."""
    provider = SentryObservabilityProvider()
    secret = "my_sentry_secret_key"
    payload = b'{"event_id": "123", "title": "Test Sentry Exception"}'

    # Compute valid signature
    import hmac, hashlib
    valid_sig = hmac.new(secret.encode('utf-8'), payload, hashlib.sha256).hexdigest()

    assert provider.verify_webhook({"sentry-hook-signature": valid_sig}, payload, secret=secret) is True
    assert provider.verify_webhook({"sentry-hook-signature": "invalid-sig"}, payload, secret=secret) is False
    assert provider.verify_webhook({"sentry-hook-signature": "invalid-sentry-sig"}, payload) is False


def test_generic_webhook_signature_verification():
    """Verify Generic Webhook HMAC signature validation."""
    provider = GenericWebhookProvider()
    secret = "generic_secret_123"
    payload = b'{"message": "Test Generic Error"}'

    import hmac, hashlib
    valid_sig = hmac.new(secret.encode('utf-8'), payload, hashlib.sha256).hexdigest()

    assert provider.verify_webhook({"x-webhook-signature": valid_sig}, payload, secret=secret) is True
    assert provider.verify_webhook({"x-webhook-signature": "invalid-sig"}, payload, secret=secret) is False
    assert provider.verify_webhook({"x-webhook-signature": "invalid-generic-sig"}, payload) is False


def test_secret_redaction_in_normalizer():
    """Verify secret credentials (passwords, tokens, API keys) are scrubbed from telemetry."""
    raw_payload = {
        "message": "Failed connection to postgres://user:supersecret123@localhost:5432/db with token ghp_1234567890abcdefghijklmnopqrstuvwx",
        "stack_trace": "File 'app.py', line 10, key='sk-proj-999999999999'",
        "api_key": "sk-proj-secret-key-123",
        "db": {"password": "my_db_password_123"}
    }
    normalized = ObservabilityNormalizer.normalize_generic(raw_payload)

    assert "supersecret123" not in normalized.message
    assert "ghp_1234567890abcdefghijklmnopqrstuvwx" not in normalized.message
    assert "sk-proj-999999999999" not in (normalized.stack_trace or "")
    assert normalized.metadata_payload["api_key"] == "[REDACTED_SECRET]"
    assert normalized.metadata_payload["db"]["password"] == "[REDACTED_SECRET]"


def test_read_only_agent_tools_permissions():
    """Verify all observability agent tools enforce ToolPermission.READ_ONLY."""
    search_tool = ProductionIncidentSearchTool()
    details_tool = ProductionIncidentDetailsTool()
    correlate_tool = ProductionIncidentCorrelateTool()

    assert search_tool.permission_level == ToolPermission.READ_ONLY
    assert details_tool.permission_level == ToolPermission.READ_ONLY
    assert correlate_tool.permission_level == ToolPermission.READ_ONLY


@pytest.mark.asyncio
async def test_api_webhook_invalid_signature_rejection(client: AsyncClient):
    """Verify API returns 401 UNAUTHORIZED when webhook signature is invalid."""
    res = await client.post(
        "/api/v1/observability/webhooks/mock",
        headers={"x-mock-signature": "invalid-sig"},
        json={"scenario": "INVALID_SIGNATURE"}
    )
    assert res.status_code == 401
    assert "SECURITY_POLICY_VIOLATION" in res.json()["detail"]
