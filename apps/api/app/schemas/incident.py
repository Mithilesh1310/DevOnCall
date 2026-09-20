from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict

class IncidentBase(BaseModel):
    project_id: str
    title: str
    status: str = "OPEN"
    severity: str = "MEDIUM"
    source: str = "manual"
    description: Optional[str] = None

class IncidentCreate(IncidentBase):
    pass

class RootCauseHypothesisSchema(BaseModel):
    summary: str
    confidence: float
    evidence: List[str] = []
    files: List[str] = []
    stack_frames: List[str] = []
    unknowns: List[str] = []

class ProposedFixSchema(BaseModel):
    summary: str
    files_to_change: List[str] = []
    reason: str
    expected_behavior: str
    validation_plan: List[str] = []
    risk_level: str = "LOW"

class IncidentInvestigationResponse(BaseModel):
    id: str
    incident_id: str
    status: str
    confidence: float
    hypothesis: Optional[Dict[str, Any]] = None
    evidence: Optional[List[Any]] = None
    relevant_files: Optional[List[str]] = None
    relevant_stack_frames: Optional[List[str]] = None
    repository_matches: Optional[List[Dict[str, Any]]] = None
    proposed_fix: Optional[Dict[str, Any]] = None
    recommended_next_action: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class IncidentResponse(IncidentBase):
    id: str
    external_event_id: Optional[str] = None
    external_issue_id: Optional[str] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    environment: Optional[str] = None
    release: Optional[str] = None
    commit_sha: Optional[str] = None
    culprit: Optional[str] = None
    occurrence_count: int = 1
    first_seen_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    stack_trace: Optional[List[Dict[str, Any]]] = None
    normalized_metadata: Optional[Dict[str, Any]] = None
    investigation: Optional[IncidentInvestigationResponse] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
