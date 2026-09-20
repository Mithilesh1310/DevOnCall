import pytest
from httpx import AsyncClient
from app.services.integrations.sentry import MockSentryProvider

@pytest.mark.asyncio
async def test_sentry_incident_deduplication_flow(client: AsyncClient):
    # 1. Simulate initial incident ingestion (scenario: python_attribute_error)
    res1 = await client.post("/api/v1/webhooks/sentry/simulate?scenario=python_attribute_error")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] == "INGESTED"
    assert data1["deduplicated"] is False
    incident_id = data1["incident_id"]
    issue_id = data1["issue_id"]

    # 2. Re-send identical issue via simulate endpoint
    res2 = await client.post("/api/v1/webhooks/sentry/simulate?scenario=python_attribute_error")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "UPDATED"
    assert data2["deduplicated"] is True
    assert data2["incident_id"] == incident_id
    assert data2["occurrence_count"] >= 2

    # 3. Verify incident details in GET /api/v1/incidents
    res_list = await client.get("/api/v1/incidents")
    assert res_list.status_code == 200
    incidents = res_list.json()
    target_inc = next((i for i in incidents if i["id"] == incident_id), None)
    assert target_inc is not None
    assert target_inc["external_issue_id"] == issue_id
    assert target_inc["occurrence_count"] >= 2
    assert target_inc["error_type"] == "AttributeError"
