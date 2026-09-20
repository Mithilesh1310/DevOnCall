import pytest
from app.services.deployment.security import DeploymentSecurityPolicy
from app.services.deployment.models import ApprovalType, ApprovalDecision, CanaryStatus, CanaryVerdict
from app.services.deployment.manager import DeploymentManager
from app.services.agent.registry import default_tool_registry
from app.services.agent.policies import ToolPermission


def test_commit_sha_validation_accepts_valid_sha():
    valid_sha = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
    ok, msg = DeploymentSecurityPolicy.validate_commit_sha(valid_sha)
    assert ok is True
    assert msg == "SHA_VALID"


@pytest.mark.parametrize("invalid_sha", [
    "latest",
    "main",
    "master",
    "v1.0.0",
    "devoncall/agent/fix-1",
    "12345",
    "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1bZ",  # non-hex Z
])
def test_commit_sha_validation_rejects_floating_and_invalid_tags(invalid_sha):
    ok, msg = DeploymentSecurityPolicy.validate_commit_sha(invalid_sha)
    assert ok is False
    assert "rejected" in msg.lower() or "hex" in msg.lower()


@pytest.mark.parametrize("traffic", [1.0, 5.0, 10.0])
def test_canary_traffic_bounds_accepts_valid(traffic):
    ok, msg = DeploymentSecurityPolicy.validate_canary_traffic(traffic)
    assert ok is True


@pytest.mark.parametrize("traffic", [0.0, 0.5, 10.5, 50.0, 100.0, -5.0])
def test_canary_traffic_bounds_rejects_out_of_bounds(traffic):
    ok, msg = DeploymentSecurityPolicy.validate_canary_traffic(traffic)
    assert ok is False
    assert "MUST be between 1.0% and 10.0%" in msg


def test_insufficient_data_verdict_never_converts_to_pass():
    manager = DeploymentManager()
    verif = manager.verify_canary("canary-test-1", scenario="INSUFFICIENT_DATA")
    assert verif.verdict != CanaryVerdict.PASS
    assert verif.verdict in [CanaryVerdict.HUMAN_REVIEW, CanaryVerdict.INSUFFICIENT_DATA]


def test_agent_deployment_tools_are_read_only():
    status_tool = default_tool_registry.get("release_candidate_status")
    canary_tool = default_tool_registry.get("canary_verification_details")
    audit_tool = default_tool_registry.get("deployment_audit_log")

    assert status_tool is not None
    assert status_tool.permission_level == ToolPermission.READ_ONLY

    assert canary_tool is not None
    assert canary_tool.permission_level == ToolPermission.READ_ONLY

    assert audit_tool is not None
    assert audit_tool.permission_level == ToolPermission.READ_ONLY


def test_production_provider_rejects_shell_command():
    from app.services.deployment.providers.production_provider import ProductionProvider
    provider = ProductionProvider()
    with pytest.raises(NotImplementedError) as exc_info:
        provider.execute_raw_shell("rm -rf /")
    assert "PRODUCTION = DENIED" in str(exc_info.value)


def test_confirmation_token_generation_and_expiry():
    token, expires_at = DeploymentSecurityPolicy.generate_confirmation_token("RC-101", ApprovalType.CANARY_RELEASE)
    assert len(token) > 16
    assert expires_at > 0
