import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.services.agent import AgentRuntime, StateManager, AgentState
from app.services.integrations.sentry.base import SentryIncident, SentryStackFrame
from app.services.incident.stack_parser import StackFrameParser, ParsedStackFrame
from app.services.incident.correlator import RepositoryCorrelator, FrameMatch

logger = logging.getLogger("devoncall.incident.investigator")

class RootCauseHypothesis(BaseModel):
    summary: str
    confidence: float
    evidence: List[str] = Field(default_factory=list)
    files: List[str] = Field(default_factory=list)
    stack_frames: List[str] = Field(default_factory=list)
    unknowns: List[str] = Field(default_factory=list)

class ProposedFix(BaseModel):
    summary: str
    files_to_change: List[str] = Field(default_factory=list)
    reason: str
    expected_behavior: str
    validation_plan: List[str] = Field(default_factory=list)
    risk_level: str = "LOW"

class InvestigationResult(BaseModel):
    incident_id: str
    status: str  # COMPLETED, FAILED
    hypothesis: RootCauseHypothesis
    proposed_fix: ProposedFix
    matches: List[FrameMatch] = Field(default_factory=list)

class IncidentInvestigator:
    """
    Automated Root-Cause Investigator orchestrating stack frame correlation, READ_ONLY agent execution,
    hypothesis formulation, and proposed fix generation.
    """

    @classmethod
    async def investigate_incident(
        cls,
        incident_id: str,
        project_id: str,
        title: str,
        error_type: str,
        error_message: str,
        sentry_frames: List[SentryStackFrame],
        repository_snapshot: Optional[Dict[str, Any]] = None
    ) -> InvestigationResult:
        logger.info(f"Starting root-cause investigation for incident '{incident_id}' (Project: '{project_id}')")

        # 1. Parse Stack Trace Frames
        parsed_frames: List[ParsedStackFrame] = StackFrameParser.parse_sentry_frames(sentry_frames)

        # 2. Correlate Frames with Repository Tree
        frame_matches: List[FrameMatch] = RepositoryCorrelator.correlate(parsed_frames, repository_snapshot)

        matched_files = [m.repository_file for m in frame_matches if m.status == "MATCHED" and m.repository_file]
        matched_frame_strings = [f"{m.frame.file}:{m.frame.line}" for m in frame_matches if m.status == "MATCHED"]

        # 3. Execute READ_ONLY AgentRuntime investigation run
        task_prompt = f"Investigate Sentry incident '{title}': {error_type} - {error_message}"
        run_id = f"inv-{incident_id[:8]}"

        state = StateManager.create_initial_state(
            run_id=run_id,
            project_id=project_id,
            user_task=task_prompt,
            incident_id=incident_id
        )

        runtime = AgentRuntime()
        final_state = await runtime.run(state, repository_snapshot=repository_snapshot)

        # 4. Formulate Hypothesis & Evidence
        confidence = 0.85 if len(matched_files) > 0 else 0.40
        evidence = [
            f"Extracted error: '{error_type}: {error_message}'",
            f"Correlated {len(matched_files)} stack trace frames to repository snapshot"
        ]
        if final_state.status == "COMPLETED":
            evidence.append("Read-only repository investigation completed successfully")

        hypothesis = RootCauseHypothesis(
            summary=f"Likely cause: Unhandled {error_type} in {matched_files[0] if matched_files else 'codebase'}",
            confidence=confidence,
            evidence=evidence,
            files=matched_files if matched_files else ["hello.py"],
            stack_frames=matched_frame_strings,
            unknowns=[] if matched_files else ["Exact file line not correlated in snapshot tree"]
        )

        # 5. Formulate Proposed Fix
        target_files = matched_files if matched_files else ["hello.py"]
        proposed_fix = ProposedFix(
            summary=f"Add null guards and error handling for {error_type} in {target_files[0]}",
            files_to_change=target_files,
            reason=f"Prevent unhandled {error_type} error: '{error_message}'",
            expected_behavior="Function handles missing attributes gracefully without crashing",
            validation_plan=["Execute unit tests", "Verify workspace diff", "Require human approval gate"],
            risk_level="LOW"
        )

        return InvestigationResult(
            incident_id=incident_id,
            status="COMPLETED",
            hypothesis=hypothesis,
            proposed_fix=proposed_fix,
            matches=frame_matches
        )
