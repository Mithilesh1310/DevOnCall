import pytest
from httpx import AsyncClient
from app.services.integrations.sentry import verify_sentry_signature, MockSentryProvider

@pytest.mark.asyncio
async def test_sentry_webhook_signature_verification():
    raw_body = b'{"event":{"event_id":"123"}}'

    # Without secret configured, verify_sentry_signature returns True in dev mode
    assert verify_sentry_signature(raw_body, None, secret=None) is True

    # With secret configured, valid HMAC signature passes, invalid signature fails
    secret = "my_sentry_secret_key"
    import hmac, hashlib
    valid_sig = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    assert verify_sentry_signature(raw_body, valid_sig, secret=secret) is True
    assert verify_sentry_signature(raw_body, "invalid_signature", secret=secret) is False

@pytest.mark.asyncio
async def test_simulate_sentry_webhook_endpoint(client: AsyncClient):
    res = await client.post("/api/v1/webhooks/sentry/simulate?scenario=javascript_type_error")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["INGESTED", "UPDATED"]
    assert "incident_id" in data

    # Second request with same issue should deduplicate
    res_dedup = await client.post("/api/v1/webhooks/sentry/simulate?scenario=javascript_type_error")
    assert res_dedup.status_code == 200
    data_dedup = res_dedup.json()
    assert data_dedup["status"] == "UPDATED"
    assert data_dedup["deduplicated"] is True
    assert data_dedup["occurrence_count"] >= 2
