import uuid
from datetime import datetime, timezone
from typing import Dict, Any
from app.services.integrations.sentry.base import SentryIncident, SentryStackFrame

class MockSentryProvider:
    """
    Deterministic Mock Sentry Provider for offline testing, integration simulation, and demonstrations.
    Does not require real Sentry API tokens or network webhooks.
    """

    @classmethod
    def generate_mock_payload(cls, scenario: str = "javascript_type_error") -> Dict[str, Any]:
        """
        Generates realistic Sentry raw webhook payload dictionaries.
        """
        event_id = "mock-evt-1001"
        issue_id = "mock-issue-2002"

        if scenario == "python_attribute_error":
            return {
                "action": "created",
                "data": {
                    "issue": {
                        "id": issue_id,
                        "project": {"slug": "devoncall-backend"},
                        "title": "AttributeError: 'NoneType' object has no attribute 'get'",
                        "count": 14,
                        "environment": "production",
                        "permalink": f"https://sentry.io/organizations/devoncall/issues/{issue_id}/"
                    },
                    "event": {
                        "event_id": event_id,
                        "project": "devoncall-backend",
                        "environment": "production",
                        "release": "abc123rel",
                        "exception": {
                            "values": [
                                {
                                    "type": "AttributeError",
                                    "value": "'NoneType' object has no attribute 'get'",
                                    "stacktrace": {
                                        "frames": [
                                            {"filename": "app/main.py", "lineno": 12, "function": "api_handler"},
                                            {"filename": "app/services/user.py", "lineno": 42, "function": "get_user_email"}
                                        ]
                                    }
                                }
                            ]
                        },
                        "request": {
                            "headers": {
                                "Authorization": "Bearer secret_token_12345",
                                "Cookie": "session=abcxyz"
                            }
                        }
                    }
                }
            }

        # Default: JavaScript / TypeScript null pointer error
        return {
            "action": "created",
            "data": {
                "issue": {
                    "id": issue_id,
                    "project": {"slug": "devoncall-demo"},
                    "title": "TypeError: Cannot read properties of undefined (reading 'email')",
                    "count": 42,
                    "environment": "production",
                    "permalink": f"https://sentry.io/organizations/devoncall/issues/{issue_id}/"
                },
                "event": {
                    "event_id": event_id,
                    "project": "devoncall-demo",
                    "environment": "production",
                    "release": "rel-v1.4.2",
                    "exception": {
                        "values": [
                            {
                                "type": "TypeError",
                                "value": "Cannot read properties of undefined (reading 'email')",
                                "stacktrace": {
                                    "frames": [
                                        {"filename": "src/api/users.ts", "lineno": 42, "colno": 17, "function": "getUser"},
                                        {"filename": "src/controllers/userController.ts", "lineno": 18, "colno": 5, "function": "handleGetUser"}
                                    ]
                                }
                            }
                        ]
                    },
                    "request": {
                        "headers": {
                            "Authorization": "Bearer secret_user_jwt",
                            "Cookie": "auth_cookie=secret_value"
                        }
                    }
                }
            }
        }

    @classmethod
    def get_mock_incident(cls, scenario: str = "javascript_type_error") -> SentryIncident:
        raw = cls.generate_mock_payload(scenario)
        from app.services.integrations.sentry.normalizer import SentryNormalizer
        return SentryNormalizer.normalize_event(raw, is_mock=True)
