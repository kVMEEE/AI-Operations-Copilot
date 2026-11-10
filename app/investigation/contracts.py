"""Public evidence contracts. Provider proposals cannot introduce infrastructure facts."""
from typing import Literal, Any
from pydantic import BaseModel, Field, ConfigDict

class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

class Evidence(Contract):
    id: str
    incident_id: str
    kind: Literal['log', 'metric']
    source: str
    values: dict[str, Any]
    excerpt: str = ''
    timestamp: str | None = None

class Hypothesis(Contract):
    category: str
    title: str
    supporting: list[str] = Field(default_factory=list, max_length=100)
    contradicting: list[str] = Field(default_factory=list, max_length=100)
    missing: list[str] = Field(default_factory=lambda: ['Timing, topology and deployment history are not established.'])
    heuristic_score: float | None = None
    uncertainty: Literal['low', 'moderate', 'high'] = 'high'

class Chunk(Contract):
    id: str
    document_id: str
    source: str
    heading: str
    version: str
    content_hash: str
    content: str
    score: float = 0

class Citation(Contract):
    chunk_id: str
    evidence_ids: list[str] = Field(default_factory=list, max_length=30)

class NumericClaim(Contract):
    evidence_id: str
    field: Literal['peak', 'last', 'threshold', 'frequency']
    value: float

class Diagnostic(Contract):
    action: Literal['inspect_logs', 'inspect_metrics', 'review_runbook', 'collect_timing']
    action_type: Literal['read_only', 'potentially_disruptive', 'configuration_change']
    evidence_ids: list[str] = Field(default_factory=list, max_length=30)

class Proposal(Contract):
    """Constrained claims: prose, timestamps, hostnames and execution claims are not accepted."""
    category: Literal['Database', 'Memory', 'Network', 'Disk', 'CPU', 'Unknown', 'None']
    supporting: list[str] = Field(max_length=30)
    contradicting: list[str] = Field(max_length=30)
    missing: list[Literal['timing', 'topology', 'deployment_history', 'more_telemetry']] = Field(max_length=4)
    uncertainty: Literal['low', 'moderate', 'high']
    citations: list[Citation] = Field(max_length=8)
    numeric_claims: list[NumericClaim] = Field(max_length=20)
    diagnostics: list[Diagnostic] = Field(max_length=10)

class ToolCall(Contract):
    name: Literal['get_log_evidence', 'get_metric_evidence', 'get_rule_hypotheses', 'search_runbooks', 'get_runbook_chunk']
    incident_id: str
    query: str = Field(default='', max_length=500)
    reference_id: str = Field(default='', max_length=200)

class Decision(Contract):
    tools: list[ToolCall] = Field(default_factory=list, max_length=3)
    proposal: Proposal | None = None

class Verification(Contract):
    status: Literal['passed', 'fallback']
    reasons: list[str] = Field(default_factory=list)
    semantic_support_proven: bool = False

class ProviderMetadata(Contract):
    requested: str
    active: str = 'disabled'
    model: str | None = None
    calls: int = 0
    tool_calls: int = 0
    usage: dict[str, int] = Field(default_factory=dict)
    error: str | None = None
    elapsed_ms: float = 0

class Trace(Contract):
    stage: str
    outcome: str
    reference: str | None = None

class Findings(Contract):
    engine: str
    logs: dict
    metrics: dict
    correlation: dict

class Investigation(Contract):
    evidence: list[Evidence]
    findings: Findings
    hypotheses: list[Hypothesis]
    chunks: list[Chunk] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    verification: Verification
    provider: ProviderMetadata
    retrieval_mode: str
    trace: list[Trace]
    proposal: Proposal | None = None
