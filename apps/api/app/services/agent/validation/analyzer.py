import re
import logging
from typing import List, Dict, Any, Optional
from app.services.agent.validation.models import ValidationResult, FailureDiagnostic, FailureType
from app.services.agent.validation.failure_classifier import FailureClassifier
from app.services.incident.correlator import RepositoryCorrelator
from app.services.incident.stack_parser import StackFrameParser

logger = logging.getLogger("devoncall.validation.analyzer")

class ValidationAnalyzer:
    """
    Analyzes SandboxRun outputs, extracts diagnostic line/column details, correlates files against
    RepositorySnapshot, and creates structured ValidationResult objects.
    """

    @classmethod
    def analyze(
        cls,
        sandbox_run_id: str,
        status: str,
        command_type: str,
        exit_code: int,
        stdout: str,
        stderr: str,
        repository_snapshot: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        if status == "PASSED":
            return ValidationResult(
                sandbox_run_id=sandbox_run_id,
                status="PASSED",
                command_type=command_type,
                exit_code=exit_code,
                summary=f"Validation '{command_type}' PASSED cleanly.",
                stdout=stdout,
                stderr=stderr,
                failure_type=None,
                diagnostics=[],
                affected_files=[],
                suggested_action="CONTINUE"
            )

        # Classify Failure Type
        failure_type: FailureType = FailureClassifier.classify(
            command_type=command_type,
            status=status,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr
        )

        # Extract Failure Diagnostics
        diagnostics: List[FailureDiagnostic] = cls.extract_diagnostics(stdout, stderr)

        # Correlate Diagnostic Files against Repository Snapshot
        extracted_files = [d.file for d in diagnostics if d.file]
        matched_files = cls.correlate_files(extracted_files, repository_snapshot)

        summary = f"Validation '{command_type}' FAILED ({failure_type.value}). Extracted {len(diagnostics)} diagnostics."

        return ValidationResult(
            sandbox_run_id=sandbox_run_id,
            status=status,
            command_type=command_type,
            exit_code=exit_code,
            summary=summary,
            stdout=stdout,
            stderr=stderr,
            failure_type=failure_type,
            diagnostics=diagnostics,
            affected_files=matched_files if matched_files else (extracted_files[:1] if extracted_files else []),
            suggested_action="FIX" if status == "FAILED" else ("RETRY" if status == "ERROR" else "STOP")
        )

    @classmethod
    def extract_diagnostics(cls, stdout: str, stderr: str) -> List[FailureDiagnostic]:
        diagnostics: List[FailureDiagnostic] = []
        combined = f"{stdout}\n{stderr}"
        lines = combined.splitlines()

        # Regex Pattern 1 (TypeScript / ESLint): file(line,col): error TS1234: message or file:line:col - message
        ts_pattern = re.compile(r"(?P<file>[^\s():]+\.[a-zA-Z0-9]+)\((?P<line>\d+),(?P<col>\d+)\):\s+(?:error\s+)?(?P<code>TS\d+)?:\s*(?P<msg>.+)")
        ts_pattern_alt = re.compile(r"(?P<file>[^\s():]+\.[a-zA-Z0-9]+):(?P<line>\d+):(?P<col>\d+)\s+-\s+(?:error\s+)?(?P<code>TS\d+)?:\s*(?P<msg>.+)")

        # Regex Pattern 2 (Python Pytest / Traceback): File "path/file.py", line 42, in function
        py_pattern = re.compile(r'File "(?P<file>[^"]+)", line (?P<line>\d+)(?:, in (?P<fn>.+))?')

        # Regex Pattern 3 (AssertionError): AssertionError: message
        assert_pattern = re.compile(r"(?P<msg>AssertionError:\s*.+)")

        for line_str in lines:
            clean = line_str.strip()

            m_ts = ts_pattern.search(clean) or ts_pattern_alt.search(clean)
            if m_ts:
                diagnostics.append(FailureDiagnostic(
                    message=m_ts.group("msg").strip(),
                    file=m_ts.group("file").replace("\\", "/"),
                    line=int(m_ts.group("line")),
                    column=int(m_ts.group("col")),
                    code=m_ts.group("code") if "code" in m_ts.groupdict() else None,
                    source="compiler",
                    raw_snippet=clean
                ))
                continue

            m_py = py_pattern.search(clean)
            if m_py:
                diagnostics.append(FailureDiagnostic(
                    message=f"Error in {m_py.group('fn') or 'code'}",
                    file=m_py.group("file").replace("\\", "/"),
                    line=int(m_py.group("line")),
                    column=None,
                    code=None,
                    source="traceback",
                    raw_snippet=clean
                ))
                continue

            m_assert = assert_pattern.search(clean)
            if m_assert:
                diagnostics.append(FailureDiagnostic(
                    message=m_assert.group("msg"),
                    file=None,
                    line=None,
                    column=None,
                    code="ASSERTION",
                    source="pytest",
                    raw_snippet=clean
                ))

        return diagnostics

    @classmethod
    def correlate_files(cls, raw_files: List[str], repository_snapshot: Optional[Dict[str, Any]]) -> List[str]:
        if not repository_snapshot or "tree" not in repository_snapshot:
            return list(set(raw_files))

        repo_tree = [node.get("path", "").replace("\\", "/") for node in repository_snapshot.get("tree", []) if node.get("type") == "file"]
        matched = []

        for rf in raw_files:
            clean_rf = rf.replace("\\", "/").lstrip("/")
            if clean_rf in repo_tree:
                matched.append(clean_rf)
            else:
                for rp in repo_tree:
                    if rp.endswith(clean_rf) or clean_rf.endswith(rp):
                        matched.append(rp)
                        break

        return list(dict.fromkeys(matched))
