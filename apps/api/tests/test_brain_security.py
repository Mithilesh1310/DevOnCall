import pytest
from app.services.brain.provenance import BrainSecretRedactor
from app.services.agent.tools.brain_tool import ProjectBrainQueryTool
from app.services.agent.tools.base import ToolContext
from app.services.agent.policies import ToolPermission
from app.services.integrations.whatsapp.parser import WhatsAppCommandParser
from app.services.integrations.whatsapp.policies import WhatsAppSecurityPolicy
from app.services.integrations.whatsapp.models import AuthorizedDeveloper, WhatsAppRole, CommandType


def test_brain_secret_redactor_text():
    """Verify that BrainSecretRedactor redacts passwords, tokens, API keys, DSNs, and AWS keys."""
    raw_text = (
        "Connected to postgres://user:supersecret123@localhost:5432/devoncall "
        "with token ghp_1234567890abcdefghijklmnopqrstuvwx and aws key AKIAIOSFODNN7EXAMPLE "
        "and sentry dsn https://abc:secret123@sentry.io/123."
    )
    redacted = BrainSecretRedactor.redact_text(raw_text)

    assert "supersecret123" not in redacted
    assert "ghp_1234567890abcdefghijklmnopqrstuvwx" not in redacted
    assert "AKIAIOSFODNN7EXAMPLE" not in redacted
    assert "[REDACTED" in redacted


def test_brain_secret_redactor_dict():
    """Verify that BrainSecretRedactor recursively scrubs secret dictionary keys."""
    payload = {
        "service": "api",
        "api_key": "sk-proj-123456789",
        "db": {
            "password": "my_db_password_999",
            "host": "localhost"
        },
        "config": {
            "public_id": "demo-1"
        }
    }
    redacted = BrainSecretRedactor.redact_dict(payload)

    assert redacted["api_key"] == "[REDACTED_SECRET]"
    assert redacted["db"]["password"] == "[REDACTED_SECRET]"
    assert redacted["config"]["public_id"] == "demo-1"


def test_brain_agent_tool_read_only():
    """Verify that ProjectBrainQueryTool is strictly READ_ONLY."""
    tool = ProjectBrainQueryTool()
    assert tool.name == "project_brain_query"
    assert tool.permission_level == ToolPermission.READ_ONLY


@pytest.mark.asyncio
async def test_brain_agent_tool_execution():
    """Verify executing ProjectBrainQueryTool returns structured JSON without mutating state."""
    tool = ProjectBrainQueryTool()
    ctx = ToolContext(run_id="run-demo-123", workspace_id="ws-demo", project_id="demo-project")
    result = await tool.execute(input_params={"project_id": "demo-project", "query": "service"}, context=ctx)

    assert result.success is True
    assert result.data is not None
    assert "nodes" in result.data
    assert len(result.data["nodes"]) > 0


def test_whatsapp_brain_command_authorization():
    """Verify that authorized developer can execute read-only BRAIN commands."""
    dev = AuthorizedDeveloper(
        id="dev-1",
        identity_hash="hash123",
        name="Security Tester",
        phone_number_masked="+***1234",
        project_id="demo-project",
        role=WhatsAppRole.DEVELOPER,
        enabled=True
    )

    is_auth_brain, _ = WhatsAppSecurityPolicy.authorize_command(dev, CommandType.BRAIN, "demo-project")
    assert is_auth_brain is True

    is_auth_search, _ = WhatsAppSecurityPolicy.authorize_command(dev, CommandType.BRAIN_SEARCH, "demo-project")
    assert is_auth_search is True


def test_whatsapp_brain_command_parsing():
    """Verify WhatsApp parser parses BRAIN, BRAIN SUMMARY, and BRAIN SEARCH commands."""
    cmd_summary = WhatsAppCommandParser.parse("BRAIN SUMMARY")
    assert cmd_summary.command_type == CommandType.BRAIN_SUMMARY

    cmd_search = WhatsAppCommandParser.parse("BRAIN SEARCH user auth service")
    assert cmd_search.command_type == CommandType.BRAIN_SEARCH
    assert cmd_search.incident_id == "user auth service"
