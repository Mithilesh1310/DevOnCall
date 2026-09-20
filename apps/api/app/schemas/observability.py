from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ObservationResponseSchema(BaseModel):
    id: str
    project_id: str
    provider: str
    external_event_id: str
    fingerprint: str
    event_type: str
    severity: str
    status: str
    environment: str
    service: str
    release: Optional[str] = None
    commit_sha: Optional[str] = None
    message: str
    stack_trace: Optional[str] = None
    endpoint: Optional[str] = None
    request_method: Optional[str] = None
    source_url: Optional[str] = None
    first_seen_at: str
    last_seen_at: str
    occurrence_count: int
    metadata_payload: Optional[Dict[str, Any]] = None


class IncidentCorrelationResponseSchema(BaseModel):
    observation_id: str
    project_id: str
    commit_sha: Optional[str] = None
    commit_found: bool
    affected_service: str
    affected_files: List[str]
    project_brain_nodes: List[Dict[str, Any]]
    historical_incidents: List[Dict[str, Any]]
    staging_deployments: List[Dict[str, Any]]
    temporal_deployment_correlation: Optional[str] = None
    correlation_confidence: str


class IncidentIntelligenceReportSchema(BaseModel):
    incident_id: str
    project_id: str
    provider: str
    severity: str
    status: str
    affected_service: str
    affected_endpoint: Optional[str] = None
    release: Optional[str] = None
    commit_sha: Optional[str] = None
    message: str
    verified_facts: List[str]
    correlations: List[str]
    hypotheses: List[str]
    project_brain_context: List[Dict[str, Any]]
    historical_incidents: List[Dict[str, Any]]
    likely_files: List[str]
    investigation_context: Dict[str, Any]
    proposed_next_steps: List[str]
    confidence_score: float


class UpdateStatusRequestSchema(BaseModel):
    status: str = Field(description="New status: ACKNOWLEDGED, RESOLVED, IGNORED, OPEN")
