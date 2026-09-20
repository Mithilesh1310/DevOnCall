import pytest
from app.services.integrations.sentry.base import SentryStackFrame
from app.services.incident.stack_parser import StackFrameParser

def test_parse_sentry_frames():
    sentry_frames = [
        SentryStackFrame(file="app/main.py", line=10, function="index", raw_frame=None),
        SentryStackFrame(file="src\\utils\\helper.ts", line=42, column=15, function="formatName", raw_frame=None),
    ]

    parsed = StackFrameParser.parse_sentry_frames(sentry_frames)
    assert len(parsed) == 2
    assert parsed[0].file == "app/main.py"
    assert parsed[0].line == 10
    assert parsed[0].function == "index"

    assert parsed[1].file == "src/utils/helper.ts"
    assert parsed[1].line == 42
    assert parsed[1].column == 15
    assert parsed[1].function == "formatName"

def test_parse_raw_text_trace_js():
    raw_js_trace = """
TypeError: Cannot read property 'id' of undefined
    at getUserProfile (src/services/user.ts:25:12)
    at at src/components/Card.tsx:50:5
    at render (src/index.tsx:100:2)
    """
    parsed = StackFrameParser.parse_raw_text_trace(raw_js_trace)
    assert len(parsed) >= 2
    assert parsed[0].file == "src/services/user.ts"
    assert parsed[0].line == 25
    assert parsed[0].column == 12
    assert parsed[0].function == "getUserProfile"

def test_parse_raw_text_trace_python():
    raw_py_trace = """
Traceback (most recent call last):
  File "app/main.py", line 15, in get_user
  File "app/services/user.py", line 88, in fetch_db
AttributeError: 'NoneType' object has no attribute 'query'
    """
    parsed = StackFrameParser.parse_raw_text_trace(raw_py_trace)
    assert len(parsed) == 2
    assert parsed[0].file == "app/main.py"
    assert parsed[0].line == 15
    assert parsed[0].function == "get_user"
    assert parsed[1].file == "app/services/user.py"
    assert parsed[1].line == 88
    assert parsed[1].function == "fetch_db"
