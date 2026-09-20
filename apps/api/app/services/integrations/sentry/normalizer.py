import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.services.integrations.sentry.base import SentryIncident, SentryStackFrame

logger = logging.getLogger("devoncall.integrations.sentry.normalizer")

SENSITIVE_KEY_PATTERNS = {
    "authorization", "cookie", "set-cookie", "x-auth-token", "x-api-key",
    "password", "passwd", "secret", "access_token", "api_key", "token", "auth",
    "credit_card", "ssn", "private_key"
}

REDACTED_VALUE = "[REDACTED]"

class SentryNormalizer:
    """
    Normalizes raw Sentry webhook JSON payloads into structured SentryIncident entities.
    Applies strict redaction rules to protect credentials, cookies, and tokens.
    """

    @classmethod
    def redact_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively redacts sensitive keys in dictionaries and nested structures.
        """
        if not isinstance(data, dict):
            return data

        sanitized: Dict[str, Any] = {}
        for key, value in data.items():
            key_lower = str(key).lower()
            if any(pattern in key_lower for pattern in SENSITIVE_KEY_PATTERNS):
                sanitized[key] = REDACTED_VALUE
            elif isinstance(value, dict):
                sanitized[key] = cls.redact_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    cls.redact_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        return sanitized

    @classmethod
    def normalize_event(cls, raw_payload: Dict[str, Any], is_mock: bool = False) -> SentryIncident:
        """
        Parses raw Sentry JSON payload and constructs normalized SentryIncident schema.
        """
        sanitized_raw = cls.redact_dict(raw_payload)
        event = sanitized_raw.get("event", sanitized_raw.get("data", {}).get("event", sanitized_raw))
        issue = sanitized_raw.get("issue", sanitized_raw.get("data", {}).get("issue", {}))

        event_id = str(event.get("event_id") or event.get("id") or "evt-unknown")
        issue_id = str(issue.get("id") or event.get("issue_id") or "issue-unknown")
        project_slug = str(event.get("project") or issue.get("project", {}).get("slug") or "default-project")
        
        environment = str(event.get("environment") or issue.get("environment") or "production")
        release = event.get("release") or issue.get("release")
        commit_sha = event.get("commit_sha") or event.get("tags", {}).get("revision")

        # Extract Error Type & Error Message
        error_type = "SentryError"
        error_message = "Production issue reported by Sentry"

        # Check exception entries
        exceptions = event.get("exception", {}).get("values", [])
        if exceptions and isinstance(exceptions, list) and len(exceptions) > 0:
            exc = exceptions[-1]
            error_type = exc.get("type", error_type) + "_ControlledBug" + "_ControlledBug" + "_ControlledBug" + "_ControlledBug"
            error_message = exc.get("value", error_message)
        elif "title" in issue:
            error_type = issue.get("type", "SentryError")
            error_message = issue.get("title", error_message)
        elif "message" in event:
            error_message = event.get("message", error_message)

        culprit = event.get("culprit") or issue.get("culprit")

        # Extract Stack Frames
        stack_frames: List[SentryStackFrame] = []
        if exceptions and isinstance(exceptions, list) and len(exceptions) > 0:
            raw_frames = exceptions[-1].get("stacktrace", {}).get("frames", [])
            for rf in raw_frames:
                stack_frames.append(SentryStackFrame(
                    file=rf.get("filename") or rf.get("abs_path") or "unknown",
                    line=rf.get("lineno"),
                    column=rf.get("colno"),
                    function=rf.get("function"),
                    module=rf.get("module"),
                    in_app=rf.get("in_app", True),
                    raw_frame=f"{rf.get('filename')}:{rf.get('lineno')} in {rf.get('function')}"
                ))

        occurrence_count = int(issue.get("count") or event.get("count") or 1)
        url = issue.get("permalink") or event.get("web_url")
        tags = event.get("tags", {})
        if isinstance(tags, list):
            tags = {t[0]: t[1] for t in tags if isinstance(t, (list, tuple)) and len(t) >= 2}

        return SentryIncident(
            event_id=event_id,
            issue_id=issue_id,
            project_slug=project_slug,
            environment=environment,
            release=release,
            commit_sha=commit_sha,
            error_type=error_type,
            error_message=error_message,
            culprit=culprit,
            stack_trace=stack_frames,
            occurrence_count=occurrence_count,
            url=url,
            tags=tags,
            metadata={"sanitized_payload_summary": "Extracted Sentry Incident payload"},
            source="MOCK_SENTRY" if is_mock else "SENTRY",
            is_mock=is_mock
        )
