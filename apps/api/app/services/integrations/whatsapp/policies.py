import re
from typing import Optional, List, Tuple
from app.services.integrations.whatsapp.models import AuthorizedDeveloper, WhatsAppRole, CommandType

PROMPT_INJECTION_PATTERNS = [
    re.compile(r'ignore\s+all\s+(rules|instructions|policies)', re.IGNORECASE),
    re.compile(r'bypass\s+(authorization|policy|auth)', re.IGNORECASE),
    re.compile(r'drop\s+database|rm\s+-rf|sudo\s+|eval\(|exec\(', re.IGNORECASE),
    re.compile(r'deploy\s+to\s+production|deploy\s+prod', re.IGNORECASE)
]

REDACTION_PATTERNS = [
    (re.compile(r'(password|passwd|secret|token|api_key|auth|cookie)=([^&\s]+)', re.IGNORECASE), r'\1=[REDACTED]'),
    (re.compile(r'(Authorization:\s*Bearer\s+|Bearer\s+)([^\s]+)', re.IGNORECASE), r'\1[REDACTED]'),
    (re.compile(r'postgres://[^\s]+', re.IGNORECASE), r'postgres://[REDACTED]')
]

class WhatsAppSecurityPolicy:
    """
    Enforces developer identity verification, role-based command access,
    project binding, and prompt injection neutralization for WhatsApp interface.
    """

    @staticmethod
    def is_prompt_injection(text: str) -> bool:
        if not text:
            return False
        for pattern in PROMPT_INJECTION_PATTERNS:
            if pattern.search(text):
                return True
        return False

    @staticmethod
    def authorize_command(
        developer: Optional[AuthorizedDeveloper],
        command_type: CommandType,
        project_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        if not developer:
            return False, "SENDER_UNAUTHORIZED: Developer identity not registered or recognized."

        if not developer.enabled:
            return False, "SENDER_DISABLED: Developer account is disabled."

        # Project Binding Check
        if project_id and developer.project_id != project_id and developer.role != WhatsAppRole.ADMIN:
            return False, f"PROJECT_NOT_AUTHORIZED: Developer is not mapped to project '{project_id}'."

        # Role-Based Access Control Matrix
        if command_type in [CommandType.HELP, CommandType.STATUS, CommandType.INCIDENTS, CommandType.INCIDENTS_CRITICAL, CommandType.INCIDENTS_OPEN, CommandType.INCIDENT, CommandType.DETAILS, CommandType.VALIDATION, CommandType.STAGING_STATUS, CommandType.BRAIN, CommandType.BRAIN_SUMMARY, CommandType.BRAIN_INCIDENTS, CommandType.BRAIN_SEARCH, CommandType.RELEASES, CommandType.PROJECT, CommandType.WHOAMI]:
            return True, "Authorized"

        if command_type in [CommandType.INVESTIGATE, CommandType.FIX, CommandType.STAGING, CommandType.CANARY, CommandType.CONFIRM, CommandType.CANCEL, CommandType.STOP]:
            if developer.role in [WhatsAppRole.DEVELOPER, WhatsAppRole.APPROVER, WhatsAppRole.ADMIN]:
                return True, "Authorized"
            return False, f"ROLE_DENIED: Role '{developer.role.value}' cannot execute command '{command_type.value}' (Requires DEVELOPER role or higher)."

        if command_type in [CommandType.APPROVE, CommandType.REJECT, CommandType.APPROVE_CANARY, CommandType.APPROVE_PRODUCTION, CommandType.REJECT_RELEASE, CommandType.APPROVE_ROLLBACK]:
            if developer.role in [WhatsAppRole.APPROVER, WhatsAppRole.ADMIN]:
                return True, "Authorized"
            return False, f"ROLE_DENIED: Role '{developer.role.value}' cannot execute command '{command_type.value}' (Requires APPROVER role or higher)."

        return False, "COMMAND_NOT_SUPPORTED"

class WhatsAppResponseRedactor:
    """
    Scubs secrets, bearer tokens, passwords, and private connection strings from WhatsApp responses.
    """

    @staticmethod
    def redact(text: str | None) -> str:
        if not text:
            return ""
        result = str(text)
        for pattern, replacement in REDACTION_PATTERNS:
            result = pattern.sub(replacement, result)
        return result
