from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class BrainNodeResponse(BaseModel):
    id: str
    project_id: str
    node_type: str
    key: str
    title: str
    content: str
    source_type: str
    source_reference: str
    confidence: str
    status: str
    metadata_payload: Optional[Dict[str, Any]] = None
    created_at: Any
    updated_at: Any


class BrainEdgeResponse(BaseModel):
    id: str
    project_id: str
    source_node_id: str
    target_node_id: str
    relation: str
    confidence: str
    source_reference: str
    created_at: Any


class BrainEventResponse(BaseModel):
    id: str
    project_id: str
    event_type: str
    source: str
    summary: str
    payload: Optional[Dict[str, Any]] = None
    created_at: Any


class BrainSummaryResponse(BaseModel):
    project_id: str
    total_nodes: int = 0
    total_edges: int = 0
    verified_facts_count: int = 0
    services_count: int = 0
    incidents_count: int = 0
    deployments_count: int = 0
    node_type_breakdown: Dict[str, int] = {}
    source_type_breakdown: Dict[str, int] = {}


class BrainQueryRequestSchema(BaseModel):
    query: str = ""
    node_type: Optional[str] = None
    limit: int = 20


class BrainQueryResponseSchema(BaseModel):
    nodes: List[BrainNodeResponse] = []
    edges: List[BrainEdgeResponse] = []
    events: List[BrainEventResponse] = []
    total_count: int = 0
