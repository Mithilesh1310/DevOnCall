import re
from typing import Optional
from app.services.integrations.whatsapp.models import ParsedCommand, CommandType
from app.services.integrations.whatsapp.policies import WhatsAppSecurityPolicy

class WhatsAppCommandParser:
    """
    Parses untrusted raw WhatsApp text into structured, safe command objects.
    Rejects prompt injection or malformed shell commands.
    """

    @staticmethod
    def parse(raw_text: str | None) -> ParsedCommand:
        if not raw_text or not raw_text.strip():
            return ParsedCommand(command_type=CommandType.HELP, raw_text="")

        text = raw_text.strip()

        # Prompt injection check
        if WhatsAppSecurityPolicy.is_prompt_injection(text):
            return ParsedCommand(command_type=CommandType.UNKNOWN, raw_text=text)

        parts = text.split()
        first_word = parts[0].upper().strip()

        if first_word in ["HELP", "MENU", "?"]:
            return ParsedCommand(command_type=CommandType.HELP, raw_text=text)
        elif first_word in ["STATUS", "PING"]:
            return ParsedCommand(command_type=CommandType.STATUS, raw_text=text)
        elif first_word in ["INCIDENTS", "LIST"]:
            if len(parts) >= 2 and parts[1].upper() == "CRITICAL":
                return ParsedCommand(command_type=CommandType.INCIDENTS_CRITICAL, raw_text=text)
            elif len(parts) >= 2 and parts[1].upper() == "OPEN":
                return ParsedCommand(command_type=CommandType.INCIDENTS_OPEN, raw_text=text)
            return ParsedCommand(command_type=CommandType.INCIDENTS, raw_text=text)
        elif first_word in ["PROJECT", "PROJECTS"]:
            return ParsedCommand(command_type=CommandType.PROJECT, raw_text=text)
        elif first_word in ["BRAIN", "KNOWLEDGE"]:
            if len(parts) >= 2 and parts[1].upper() == "SUMMARY":
                return ParsedCommand(command_type=CommandType.BRAIN_SUMMARY, raw_text=text)
            elif len(parts) >= 2 and parts[1].upper() == "INCIDENTS":
                return ParsedCommand(command_type=CommandType.BRAIN_INCIDENTS, raw_text=text)
            elif len(parts) >= 3 and parts[1].upper() == "SEARCH":
                query_str = " ".join(parts[2:])
                return ParsedCommand(command_type=CommandType.BRAIN_SEARCH, incident_id=query_str, raw_text=text)
            return ParsedCommand(command_type=CommandType.BRAIN, raw_text=text)
        elif first_word in ["RELEASES", "CANDIDATES"]:
            return ParsedCommand(command_type=CommandType.RELEASES, raw_text=text)
        elif first_word in ["WHOAMI", "ME", "USER"]:
            return ParsedCommand(command_type=CommandType.WHOAMI, raw_text=text)

        # Multi-word approvals: APPROVE CANARY, APPROVE PRODUCTION, REJECT RELEASE, APPROVE ROLLBACK
        upper_text = text.upper()
        if "APPROVE CANARY" in upper_text or "APPROVE_CANARY" in upper_text:
            rc_target = parts[2] if len(parts) >= 3 else (parts[1] if len(parts) >= 2 else None)
            token_arg = parts[3] if len(parts) >= 4 else None
            return ParsedCommand(command_type=CommandType.APPROVE_CANARY, target_id=rc_target, token=token_arg, raw_text=text)
        elif "APPROVE PRODUCTION" in upper_text or "APPROVE_PRODUCTION" in upper_text or "APPROVE PROD" in upper_text:
            rc_target = parts[2] if len(parts) >= 3 else (parts[1] if len(parts) >= 2 else None)
            token_arg = parts[3] if len(parts) >= 4 else None
            return ParsedCommand(command_type=CommandType.APPROVE_PRODUCTION, target_id=rc_target, token=token_arg, raw_text=text)
        elif "REJECT RELEASE" in upper_text or "REJECT_RELEASE" in upper_text:
            rc_target = parts[2] if len(parts) >= 3 else (parts[1] if len(parts) >= 2 else None)
            return ParsedCommand(command_type=CommandType.REJECT_RELEASE, target_id=rc_target, raw_text=text)
        elif "APPROVE ROLLBACK" in upper_text or "APPROVE_ROLLBACK" in upper_text:
            rc_target = parts[2] if len(parts) >= 3 else (parts[1] if len(parts) >= 2 else None)
            token_arg = parts[3] if len(parts) >= 4 else None
            return ParsedCommand(command_type=CommandType.APPROVE_ROLLBACK, target_id=rc_target, token=token_arg, raw_text=text)

        # Single or multi-arg commands
        if len(parts) >= 2:
            arg1 = parts[1].replace("#", "").strip()
            page = 1
            if len(parts) >= 3 and parts[2].isdigit():
                page = int(parts[2])

            if first_word in ["INCIDENT", "SHOW"]:
                return ParsedCommand(command_type=CommandType.INCIDENT, incident_id=arg1, page=page, raw_text=text)
            elif first_word in ["CANARY"]:
                return ParsedCommand(command_type=CommandType.CANARY, target_id=arg1, raw_text=text)
            elif first_word in ["INVESTIGATE", "ANALYZE"]:
                return ParsedCommand(command_type=CommandType.INVESTIGATE, incident_id=arg1, raw_text=text)
            elif first_word in ["DETAILS", "DETAIL"]:
                return ParsedCommand(command_type=CommandType.DETAILS, incident_id=arg1, page=page, raw_text=text)
            elif first_word in ["FIX", "REPAIR"]:
                return ParsedCommand(command_type=CommandType.FIX, incident_id=arg1, raw_text=text)
            elif first_word in ["CONFIRM", "CONF"]:
                return ParsedCommand(command_type=CommandType.CONFIRM, incident_id=arg1, token=arg1, raw_text=text)
            elif first_word in ["CANCEL", "ABORT"]:
                return ParsedCommand(command_type=CommandType.CANCEL, incident_id=arg1, raw_text=text)
            elif first_word in ["APPROVE", "PASS"]:
                return ParsedCommand(command_type=CommandType.APPROVE, incident_id=arg1, raw_text=text)
            elif first_word in ["REJECT", "DENY"]:
                return ParsedCommand(command_type=CommandType.REJECT, incident_id=arg1, raw_text=text)
            elif first_word in ["VALIDATION", "TESTS", "BUILD"]:
                return ParsedCommand(command_type=CommandType.VALIDATION, incident_id=arg1, raw_text=text)
            elif first_word in ["STAGING_STATUS"]:
                return ParsedCommand(command_type=CommandType.STAGING_STATUS, incident_id=arg1, raw_text=text)
            elif first_word in ["STAGING", "STAGE", "DEPLOY_STAGE"]:
                return ParsedCommand(command_type=CommandType.STAGING, incident_id=arg1, raw_text=text)
            elif first_word in ["STOP", "KILL"]:
                return ParsedCommand(command_type=CommandType.STOP, incident_id=arg1, raw_text=text)


        return ParsedCommand(command_type=CommandType.UNKNOWN, raw_text=text)
