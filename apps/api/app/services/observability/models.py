from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class ObservabilitySeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ObservabilityStatus(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"
    IGNORED = "IGNORED"


class ObservabilityProviderType(str, Enum):
    MOCK = "MOCK"
    SENTRY = "SENTRY"
    GENERIC = "GENERIC"


class ProductionObservationData(BaseModel):
    """
    Normalized observation domain object representing a production telemetry event.
    Strictly READ_ONLY — does NOT contain writable production operations.
    """
    id: Optional[str] = None
    project_id: str = "demo-project"
    provider: ObservabilityProviderType = ObservabilityProviderType.GENERIC
    external_event_id: str
    fingerprint: str
    event_type: str = "error"
    severity: ObservabilitySeverity = ObservabilitySeverity.ERROR
    status: ObservabilityStatus = ObservabilityStatus.OPEN
    environment: str = "PRODUCTION"
    service: str = "unknown-service"
    release: Optional[str] = None
    commit_sha: Optional[str] = None
    message: str
    stack_trace: Optional[str] = None
    endpoint: Optional[str] = None
    request_method: Optional[str] = None
    source_url: Optional[str] = None
    first_seen_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_seen_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    occurrence_count: int = 1
    metadata_payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class IncidentCorrelationData(BaseModel):
    """
    Correlated contextual information linking production observation with repository,
    Project Brain nodes, historical incidents, and staging deployment gates.
    """
    observation_id: str
    project_id: str
    commit_sha: Optional[str] = None
    commit_found: bool = False
    affected_service: str
    affected_files: List[str] = Field(default_factory=list)
    project_brain_nodes: List[Dict[str, Any]] = Field(default_factory=list)
    historical_incidents: List[Dict[str, Any]] = Field(default_factory=list)
    staging_deployments: List[Dict[str, Any]] = Field(default_factory=list)
    temporal_deployment_correlation: Optional[str] = None
    correlation_confidence: str = "MEDIUM"


class IncidentIntelligenceReport(BaseModel):
    """
    Structured Incident Intelligence Report explicitly separating VERIFIED FACTS,
    CORRELATIONS, and HYPOTHESES.
    """
    incident_id: str
    project_id: str
    provider: str
    severity: ObservabilitySeverity
    status: ObservabilityStatus
    affected_service: str
    affected_endpoint: Optional[str] = None
    release: Optional[str] = None
    commit_sha: Optional[str] = None
    message: str
    verified_facts: List[str] = Field(default_factory=list)
    correlations: List[str] = Field(default_factory=list)
    hypotheses: List[str] = Field(default_factory=list)
    project_brain_context: List[Dict[str, Any]] = Field(default_factory=list)
    historical_incidents: List[Dict[str, Any]] = Field(default_factory=list)
    likely_files: List[str] = Field(default_factory=list)
    investigation_context: Dict[str, Any] = Field(default_factory=dict)
    proposed_next_steps: List[str] = Field(default_factory=list)
    confidence_score: float = 0.85
