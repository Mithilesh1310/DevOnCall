import uuid
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class BrainNodeType(str, Enum):
    PROJECT = "PROJECT"
    SERVICE = "SERVICE"
    FILE = "FILE"
    DIRECTORY = "DIRECTORY"
    API = "API"
    DATABASE = "DATABASE"
    DEPENDENCY = "DEPENDENCY"
    INCIDENT = "INCIDENT"
    ROOT_CAUSE = "ROOT_CAUSE"
    FIX = "FIX"
    TEST = "TEST"
    DEPLOYMENT = "DEPLOYMENT"
    DECISION = "DECISION"
    CONSTRAINT = "CONSTRAINT"


class BrainSourceType(str, Enum):
    REPOSITORY_SCAN = "REPOSITORY_SCAN"
    INCIDENT = "INCIDENT"
    VALIDATION = "VALIDATION"
    STAGING = "STAGING"
    HUMAN = "HUMAN"
    SYSTEM = "SYSTEM"


class BrainConfidence(str, Enum):
    VERIFIED = "VERIFIED"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class BrainRelationType(str, Enum):
    CONTAINS = "CONTAINS"
    DEPENDS_ON = "DEPENDS_ON"
    CALLS = "CALLS"
    IMPLEMENTS = "IMPLEMENTS"
    AFFECTS = "AFFECTS"
    CAUSED_BY = "CAUSED_BY"
    FIXED_BY = "FIXED_BY"
    VALIDATED_BY = "VALIDATED_BY"
    DEPLOYED_AS = "DEPLOYED_AS"
    RELATED_TO = "RELATED_TO"
    CONSTRAINED_BY = "CONSTRAINED_BY"


class BrainNode(BaseModel):
    id: str = Field(default_factory=lambda: f"node-{uuid.uuid4().hex[:8]}")
    project_id: str
    node_type: BrainNodeType
    key: str  # Unique key for deduplication e.g. "service:apps/api" or "file:src/index.ts"
    title: str
    content: str
    source_type: BrainSourceType = BrainSourceType.REPOSITORY_SCAN
    source_reference: str
    confidence: BrainConfidence = BrainConfidence.VERIFIED
    status: str = "ACTIVE"
    metadata_payload: Optional[Dict[str, Any]] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class BrainEdge(BaseModel):
    id: str = Field(default_factory=lambda: f"edge-{uuid.uuid4().hex[:8]}")
    project_id: str
    source_node_id: str
    target_node_id: str
    relation: BrainRelationType
    confidence: BrainConfidence = BrainConfidence.VERIFIED
    source_reference: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class BrainEvent(BaseModel):
    id: str = Field(default_factory=lambda: f"evt-{uuid.uuid4().hex[:8]}")
    project_id: str
    event_type: str  # NODE_CREATED, FACT_UPDATED, CONFLICT_DETECTED, INCIDENT_ADDED, VALIDATION_RECORDED, STAGING_RECORDED
    source: str
    summary: str
    payload: Optional[Dict[str, Any]] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class BrainSummary(BaseModel):
    project_id: str
    total_nodes: int = 0
    total_edges: int = 0
    verified_facts_count: int = 0
    services_count: int = 0
    incidents_count: int = 0
    deployments_count: int = 0
    node_type_breakdown: Dict[str, int] = {}
    source_type_breakdown: Dict[str, int] = {}


class BrainQueryRequest(BaseModel):
    project_id: str
    query: Optional[str] = None
    node_type: Optional[BrainNodeType] = None
    min_confidence: Optional[BrainConfidence] = None
    file_path: Optional[str] = None
    limit: int = 20


class BrainQueryResponse(BaseModel):
    nodes: List[BrainNode] = []
    edges: List[BrainEdge] = []
    events: List[BrainEvent] = []
    total_count: int = 0
