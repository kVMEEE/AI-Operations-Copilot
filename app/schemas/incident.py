from pydantic import BaseModel, Field, field_validator
import math
from typing import List, Dict, Optional, Any
from uuid import UUID
from datetime import datetime

# --- Input Models ---

class IncidentCreate(BaseModel):
    description: str = Field(..., min_length=1, max_length=10000, example="High latency in API endpoint")
    logs: List[str] = Field(default_factory=list, example=["[ERROR] Connection timeout", "[INFO] Retrying..."])
    metrics: Dict[str, Any] = Field(default_factory=dict, example={"cpu_usage": 85.0, "latency_ms": [200, 500, 1200]})

    @field_validator("logs")
    @classmethod
    def bound_logs(cls, value):
        if len(value) > 2000 or sum(map(len, value)) > 500000:
            raise ValueError("Logs exceed 2000 entries or 500000 characters")
        return value

    @field_validator("metrics")
    @classmethod
    def numeric_metrics(cls, value):
        if len(value) > 100:
            raise ValueError("At most 100 metrics are supported")
        for name, samples in value.items():
            if not name or len(name) > 128:
                raise ValueError("Metric names must contain 1–128 characters")
            values = samples if isinstance(samples, list) else [samples]
            if not values or len(values) > 10000:
                raise ValueError("Metric series must contain 1–10000 samples")
            if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in values):
                raise ValueError("Metrics require finite numeric scalars or series")
        return value

class IncidentResponse(IncidentCreate):
    id: UUID
    status: str
    created_at: datetime

# --- Agent Output Models ---

class LogPattern(BaseModel):
    pattern: str
    frequency: int
    severity: str = "Medium"
    sample_lines: List[str] = Field(default_factory=list)

class LogAnalysisResult(BaseModel):
    patterns: List[LogPattern] = Field(default_factory=list)
    total_logs: int = 0
    error_count: int = 0
    warning_count: int = 0
    engine: Optional[str] = None

class MetricAnomaly(BaseModel):
    metric_name: str
    timestamp: Optional[str] = None
    value: float
    peak_value: Optional[float] = None
    threshold: float
    z_score: Optional[float] = None
    severity: str = "High"
    description: str

class MetricsAnalysisResult(BaseModel):
    anomalies: List[MetricAnomaly] = Field(default_factory=list)
    total_metrics_evaluated: int = 0
    has_critical_anomaly: bool = False
    engine: Optional[str] = None

class RootCause(BaseModel):
    cause: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    primary_category: Optional[str] = "Unknown"
    contributing_factors: List[str] = Field(default_factory=list)
    engine: Optional[str] = None

class Recommendation(BaseModel):
    action: str
    description: str
    is_safe: bool = True
    priority: str = "High"

class PostmortemArtifacts(BaseModel):
    logs_result: Optional[LogAnalysisResult] = None
    metrics_result: Optional[MetricsAnalysisResult] = None

class ReportContent(BaseModel):
    summary: str
    root_cause: RootCause
    recommendations: List[Recommendation]
    generated_at: datetime
    engine_version: Optional[str] = None
    artifacts: Optional[PostmortemArtifacts] = None

# --- Job Status Model ---

class JobStatus(BaseModel):
    job_id: UUID
    status: str  # initializing, processing, completed, failed
    step: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    description: Optional[str] = None
    result: Optional[ReportContent] = None
