import os
import json
import base64
from typing import List, Optional
from app.services.browser.policies import CredentialRedactor

MAX_SCREENSHOT_SIZE_MB = 5
MAX_CONSOLE_EVENTS = 100
MAX_CONSOLE_OUTPUT_BYTES = 50000

class BrowserArtifactManager:
    """
    Manages persistence of browser screenshots, console logs, and network error logs.
    Enforces safe paths (preventing path traversal) and strict file size limits.
    """

    def __init__(self, base_artifact_dir: str = "workspaces"):
        self.base_artifact_dir = os.path.abspath(base_artifact_dir)

    def _resolve_safe_path(self, workspace_id: str, filename: str) -> str:
        # Sanitize filename
        safe_filename = os.path.basename(filename)
        target_dir = os.path.abspath(os.path.join(self.base_artifact_dir, workspace_id, "artifacts"))

        # Verify path traversal stays inside workspace artifacts dir
        if not target_dir.startswith(self.base_artifact_dir):
            raise ValueError(f"Path traversal detected: {workspace_id}")

        os.makedirs(target_dir, exist_ok=True)
        return os.path.join(target_dir, safe_filename)

    def save_screenshot(self, workspace_id: str, filename: str, image_bytes: bytes) -> str:
        size_mb = len(image_bytes) / (1024 * 1024)
        if size_mb > MAX_SCREENSHOT_SIZE_MB:
            raise ValueError(f"Screenshot size {size_mb:.2f} MB exceeds limit of {MAX_SCREENSHOT_SIZE_MB} MB")

        file_path = self._resolve_safe_path(workspace_id, filename)
        with open(file_path, "wb") as f:
            f.write(image_bytes)

        return file_path

    def save_console_logs(self, workspace_id: str, filename: str, logs: List[dict]) -> str:
        truncated_logs = logs[:MAX_CONSOLE_EVENTS]
        redacted_logs = []
        for entry in truncated_logs:
            redacted_entry = {
                "level": entry.get("level", "INFO"),
                "text": CredentialRedactor.redact(entry.get("text", "")),
                "location": entry.get("location"),
                "timestamp": entry.get("timestamp")
            }
            redacted_logs.append(redacted_entry)

        content = json.dumps(redacted_logs, indent=2)
        if len(content.encode('utf-8')) > MAX_CONSOLE_OUTPUT_BYTES:
            content = content[:MAX_CONSOLE_OUTPUT_BYTES] + "\n...[TRUNCATED]"

        file_path = self._resolve_safe_path(workspace_id, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return file_path

    def save_network_logs(self, workspace_id: str, filename: str, logs: List[dict]) -> str:
        redacted_logs = []
        for entry in logs:
            redacted_entry = {
                "url": CredentialRedactor.redact(entry.get("url", "")),
                "method": entry.get("method", "GET"),
                "status_code": entry.get("status_code", 0),
                "resource_type": entry.get("resource_type"),
                "failure_text": CredentialRedactor.redact(entry.get("failure_text", ""))
            }
            redacted_logs.append(redacted_entry)

        content = json.dumps(redacted_logs, indent=2)
        file_path = self._resolve_safe_path(workspace_id, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return file_path
