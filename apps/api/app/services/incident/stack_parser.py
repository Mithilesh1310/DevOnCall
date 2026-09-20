import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.services.integrations.sentry.base import SentryStackFrame

class ParsedStackFrame(BaseModel):
    file: str
    line: Optional[int] = None
    column: Optional[int] = None
    function: Optional[str] = None
    raw_frame: str

class StackFrameParser:
    """
    Deterministic stack trace parser for JavaScript/TypeScript and Python frames.
    """

    @classmethod
    def parse_sentry_frames(cls, frames: List[SentryStackFrame]) -> List[ParsedStackFrame]:
        parsed = []
        for f in frames:
            clean_file = f.file.replace("\\", "/")
            parsed.append(ParsedStackFrame(
                file=clean_file,
                line=f.line,
                column=f.column,
                function=f.function or "anonymous",
                raw_frame=f.raw_frame or f"{clean_file}:{f.line} in {f.function}"
            ))
        return parsed

    @classmethod
    def parse_raw_text_trace(cls, text: str) -> List[ParsedStackFrame]:
        frames = []
        lines = text.splitlines()

        # Regex patterns for JS/TS and Python traces
        # Pattern 1 (JS/TS): at function (path/file.ext:line:col) or at path/file.ext:line:col
        js_pattern = re.compile(r"at\s+(?:(?P<fn>[^\s(]+)\s+\()?(?P<file>[^\s():]+):(?P<line>\d+)(?::(?P<col>\d+))?\)?")
        # Pattern 2 (Python): File "path/file.py", line 42, in func
        py_pattern = re.compile(r'File "(?P<file>[^"]+)", line (?P<line>\d+)(?:, in (?P<fn>.+))?')

        for line in lines:
            line_str = line.strip()
            # Try JS match
            m_js = js_pattern.search(line_str)
            if m_js:
                frames.append(ParsedStackFrame(
                    file=m_js.group("file").replace("\\", "/"),
                    line=int(m_js.group("line")),
                    column=int(m_js.group("col")) if m_js.group("col") else None,
                    function=m_js.group("fn") or "anonymous",
                    raw_frame=line_str
                ))
                continue

            # Try Py match
            m_py = py_pattern.search(line_str)
            if m_py:
                frames.append(ParsedStackFrame(
                    file=m_py.group("file").replace("\\", "/"),
                    line=int(m_py.group("line")),
                    column=None,
                    function=m_py.group("fn") or "<module>",
                    raw_frame=line_str
                ))
                continue

        return frames
