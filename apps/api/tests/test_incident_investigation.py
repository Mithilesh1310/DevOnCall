import pytest
from app.services.integrations.sentry.base import SentryStackFrame
from app.services.incident.investigator import IncidentInvestigator

@pytest.mark.asyncio
async def test_incident_investigation_workflow():
    sentry_frames = [
        SentryStackFrame(file="app/services/user.py", line=45, function="get_user", raw_frame=None),
    ]
    snapshot = {
        "tree": [
            {"path": "app/services/user.py", "type": "file"},
            {"path": "app/main.py", "type": "file"}
        ]
    }

    result = await IncidentInvestigator.investigate_incident(
        incident_id="inc-test-100",
        project_id="proj-test-1",
        title="AttributeError: 'NoneType' object has no attribute 'name'",
        error_type="AttributeError",
        error_message="'NoneType' object has no attribute 'name'",
        sentry_frames=sentry_frames,
        repository_snapshot=snapshot
    )

    assert result.incident_id == "inc-test-100"
    assert result.status == "COMPLETED"
    assert result.hypothesis.confidence == 0.85
    assert "app/services/user.py" in result.hypothesis.files
    assert len(result.proposed_fix.files_to_change) > 0
    assert "app/services/user.py" in result.proposed_fix.files_to_change
    assert result.proposed_fix.risk_level == "LOW"
    assert len(result.matches) == 1
    assert result.matches[0].status == "MATCHED"
