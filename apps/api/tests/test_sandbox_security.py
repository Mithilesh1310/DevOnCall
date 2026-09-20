import pytest
from app.services.sandbox import SandboxSecurityPolicy, CommandType, DockerSandboxProvider
from app.services.sandbox.limits import SandboxLimits
from app.services.agent.policies import AgentPolicy, ToolPermission, default_phase3_policy, default_phase5_policy
from app.services.agent.registry import default_tool_registry

def test_arbitrary_shell_command_rejection():
    # Only allowed CommandType enums (TEST, BUILD, LINT, TYPECHECK) can be resolved
    cmd = SandboxSecurityPolicy.resolve_command(CommandType.TEST, runtime="python")
    assert cmd == "pytest"

    cmd_node = SandboxSecurityPolicy.resolve_command(CommandType.BUILD, runtime="node")
    assert cmd_node == "npm run build"

    # Arbitrary strings raise ValueError
    with pytest.raises(ValueError):
        CommandType("rm -rf /; echo hack")

def test_permissions_policy_enforcement():
    # Phase 3 policy denies EXECUTE_SANDBOX permission
    assert default_phase3_policy.is_permission_allowed(ToolPermission.EXECUTE_SANDBOX) is False

    # Phase 5 policy allows READ_ONLY, WRITE_WORKSPACE, EXECUTE_SANDBOX but denies PRODUCTION
    assert default_phase5_policy.is_permission_allowed(ToolPermission.READ_ONLY) is True
    assert default_phase5_policy.is_permission_allowed(ToolPermission.WRITE_WORKSPACE) is True
    assert default_phase5_policy.is_permission_allowed(ToolPermission.EXECUTE_SANDBOX) is True
    assert default_phase5_policy.is_permission_allowed(ToolPermission.PRODUCTION) is False

def test_pinned_docker_images():
    assert SandboxSecurityPolicy.get_docker_image("python") == "python:3.11-slim"
    assert SandboxSecurityPolicy.get_docker_image("node") == "node:20-slim"
    assert SandboxSecurityPolicy.get_docker_image("typescript") == "node:20-slim"

    with pytest.raises(ValueError):
        SandboxSecurityPolicy.get_docker_image("unsupported_ruby_runtime")

def test_network_disabled_policy():
    assert SandboxSecurityPolicy.NETWORK_ENABLED is False

def test_resource_limits_configuration():
    limits = SandboxLimits()
    assert limits.cpu_limit == 2.0
    assert limits.memory_limit == "1g"
    assert limits.timeout_seconds == 120
    assert limits.max_output_bytes == 2097152

@pytest.mark.asyncio
async def test_docker_unavailable_handling():
    provider = DockerSandboxProvider()
    # When docker is unavailable, run_validation produces status BLOCKED with DOCKER_UNAVAILABLE error message
    is_avail = await provider.is_available()
    if not is_avail:
        res = await provider.run_validation(
            workspace_path="workspaces/demo",
            command_type=CommandType.TEST,
            command_str="pytest"
        )
        assert res.status == "BLOCKED"
        assert "DOCKER_UNAVAILABLE" in res.stderr
