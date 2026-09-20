import pytest
from app.services.browser.policies import BrowserSecurityPolicy, CredentialRedactor
from app.services.browser.artifacts import BrowserArtifactManager
from app.services.agent.policies import AgentPolicy, ToolPermission, default_phase7_policy
from app.services.agent.registry import ToolRegistry, create_default_registry

def test_url_allowlist_security():
    policy = BrowserSecurityPolicy(allowed_base_urls=["http://localhost:3000"])

    # Valid
    is_valid, _ = policy.validate_url("http://localhost:3000/login")
    assert is_valid is True

    # Invalid host/port
    is_valid, reason = policy.validate_url("http://evil.com/login")
    assert is_valid is False
    assert "not in allowed base URLs allowlist" in reason

    is_valid, reason = policy.validate_url("http://localhost:8080/login")
    assert is_valid is False

def test_forbidden_schemes_rejection():
    policy = BrowserSecurityPolicy()

    for scheme in ["file:///etc/passwd", "chrome://version", "data:text/html,hack", "javascript:alert(1)"]:
        is_valid, reason = policy.validate_url(scheme)
        assert is_valid is False, f"Should reject scheme: {scheme}"

def test_cloud_metadata_rejection():
    policy = BrowserSecurityPolicy()

    is_valid, reason = policy.validate_url("http://169.254.169.254/latest/meta-data")
    assert is_valid is False
    assert "metadata" in reason.lower()

    is_valid, reason = policy.validate_url("http://metadata.google.internal/computeMetadata/v1")
    assert is_valid is False

def test_forbidden_ports_rejection():
    policy = BrowserSecurityPolicy(allowed_base_urls=["http://localhost:22", "http://localhost:5432"])

    is_valid, reason = policy.validate_url("http://localhost:22")
    assert is_valid is False
    assert "forbidden infrastructure port" in reason

    is_valid, reason = policy.validate_url("http://localhost:5432")
    assert is_valid is False

def test_credential_redaction():
    text = "User entered password=supersecret123 and Authorization: Bearer abc123xyz"
    redacted = CredentialRedactor.redact(text)

    assert "supersecret123" not in redacted
    assert "abc123xyz" not in redacted
    assert "[REDACTED]" in redacted

def test_artifact_path_traversal_protection(tmp_path):
    mgr = BrowserArtifactManager(base_artifact_dir=str(tmp_path))

    with pytest.raises(ValueError, match="Path traversal"):
        mgr._resolve_safe_path("../../../etc", "hack.png")

def test_browser_permission_enforcement():
    registry = create_default_registry()
    tool = registry.get("browser_validate")
    assert tool is not None
    assert tool.permission_level == ToolPermission.BROWSER_SANDBOX

    # Allowed in phase 7 policy
    allowed, _ = registry.is_allowed("browser_validate", default_phase7_policy)
    assert allowed is True

    # Denied in read-only phase 2 policy
    phase2_policy = AgentPolicy({ToolPermission.READ_ONLY})
    allowed, reason = registry.is_allowed("browser_validate", phase2_policy)
    assert allowed is False
    assert "requires permission 'BROWSER_SANDBOX'" in reason

    # Production remains strictly denied
    assert ToolPermission.PRODUCTION not in default_phase7_policy.allowed_permissions
