from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from uuid import UUID
from datetime import datetime

# --- Input Models ---

class IncidentCreate(BaseModel):
    description: str = Field(..., example="High latency in API endpoint")
    logs: List[str] = Field(default_factory=list, example=["[ERROR] Connection timeout", "[INFO] Retrying..."])
    # Metrics can be a dict of time-series data or simplified key-values for now
    metrics: Dict[str, Any] = Field(default_factory=dict, example={"cpu_usage": "85%", "latency_ms": [200, 500, 1200]})

class IncidentResponse(IncidentCreate):
    id: UUID
    status: str
    created_at: datetime
    
# --- Agent Output Models ---

class LogPattern(BaseModel):
    pattern: str
    frequency: int
    severity: str

class LogAnalysisResult(BaseModel):
    patterns: List[LogPattern]
    total_logs: int

class MetricAnomaly(BaseModel):
    metric_name: str
    timestamp: Optional[str] = None
    value: float
    threshold: float
    description: str

class MetricsAnalysisResult(BaseModel):
    anomalies: List[MetricAnomaly]

class RootCause(BaseModel):
    cause: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    reasoning: str

class Recommendation(BaseModel):
    action: str
    description: str
    is_safe: bool = True

class ReportContent(BaseModel):
    summary: str
    root_cause: RootCause
    recommendations: List[Recommendation]
    generated_at: datetime

# --- Job Status Model ---

class JobStatus(BaseModel):
    job_id: UUID
    status: str  # processing, completed, failed
    step: Optional[str] = None
    result: Optional[ReportContent] = None
