import pytest
from app.services.integrations.whatsapp.parser import WhatsAppCommandParser
from app.services.integrations.whatsapp.sender import MessageFormatter
from app.services.integrations.whatsapp.mock_provider import MockWhatsAppProvider
from app.services.integrations.whatsapp.webhook import WhatsAppWebhookHandler
from app.services.integrations.whatsapp.models import CommandType, AuthorizedDeveloper, WhatsAppRole
from app.services.integrations.whatsapp.manager import WhatsAppManager


def test_command_parser_variations():
    # HELP
    cmd = WhatsAppCommandParser.parse("help")
    assert cmd.command_type == CommandType.HELP

    # INCIDENTS
    cmd = WhatsAppCommandParser.parse("incidents")
    assert cmd.command_type == CommandType.INCIDENTS

    # INCIDENT 142
    cmd = WhatsAppCommandParser.parse("INCIDENT 142")
    assert cmd.command_type == CommandType.INCIDENT
    assert cmd.incident_id == "142"

    # INVESTIGATE 142
    cmd = WhatsAppCommandParser.parse("investigate 142")
    assert cmd.command_type == CommandType.INVESTIGATE
    assert cmd.incident_id == "142"

    # FIX 142
    cmd = WhatsAppCommandParser.parse("fix 142")
    assert cmd.command_type == CommandType.FIX
    assert cmd.incident_id == "142"

    # CONFIRM A1B2C3
    cmd = WhatsAppCommandParser.parse("CONFIRM A1B2C3")
    assert cmd.command_type == CommandType.CONFIRM

    # DETAILS 142 2
    cmd = WhatsAppCommandParser.parse("details 142 2")
    assert cmd.command_type == CommandType.DETAILS
    assert cmd.incident_id == "142"
    assert cmd.page == 2

    # UNKNOWN
    cmd = WhatsAppCommandParser.parse("random unrecognized text")
    assert cmd.command_type == CommandType.UNKNOWN


def test_message_formatter_concise_truncation():
    inc = {
        "id": "142-abc",
        "title": "TypeError: Cannot read property 'map' of undefined",
        "severity": "HIGH",
        "status": "OPEN",
        "occurrence_count": 42,
        "environment": "production",
        "culprit": "src/components/UserList.tsx",
    }

    formatted = MessageFormatter.format_incident_notification(inc)
    assert "Incident #142-abc" in formatted
    assert "TypeError:" in formatted
    assert len(formatted) <= 1500


def test_webhook_challenge_verification():
    # Valid challenge
    is_valid, challenge = WhatsAppWebhookHandler.verify_webhook_challenge(
        mode="subscribe",
        token="test_token",
        challenge="ch_12345",
        expected_token="test_token"
    )
    assert is_valid is True
    assert challenge == "ch_12345"

    # Token mismatch
    is_valid_bad, _ = WhatsAppWebhookHandler.verify_webhook_challenge(
        mode="subscribe",
        token="wrong_token",
        challenge="ch_12345",
        expected_token="test_token"
    )
    assert is_valid_bad is False


@pytest.mark.asyncio
async def test_mock_whatsapp_provider():
    provider = MockWhatsAppProvider()
    res = await provider.send_message(
        recipient_phone_hash="hash123",
        text="Hello Developer",
        conversation_id="conv-123"
    )
    assert res.recipient_phone_hash == "hash123"
    assert res.text == "Hello Developer"
    assert res.conversation_id == "conv-123"


@pytest.mark.asyncio
async def test_whatsapp_manager_flow(db_session):
    provider = MockWhatsAppProvider()
    manager = WhatsAppManager(provider=provider, use_mock=True)

    res = await manager.process_message(
        db=db_session,
        raw_message_text="INCIDENTS",
        sender_phone="+14155552671",
        provider_message_id="msg-100"
    )

    assert res.text is not None
    assert "Incident" in res.text or "Queue" in res.text
