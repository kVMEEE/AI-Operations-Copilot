from pydantic import BaseModel, Field, field_validator
import math
import re
from typing import Literal
from app.investigation.contracts import Investigation
from typing import List, Dict, Optional, Any
from uuid import UUID
from datetime import datetime

# --- Input Models ---

class IncidentCreate(BaseModel):
    mode: Literal["deterministic", "llm"] = "deterministic"
    description: str = Field(..., min_length=1, max_length=10000, json_schema_extra={"example":"High latency in API endpoint"})
    logs: List[str] = Field(default_factory=list, json_schema_extra={"example":["[ERROR] Connection timeout", "[INFO] Retrying..."]})
    metrics: Dict[str, Any] = Field(default_factory=dict, json_schema_extra={"example":{"cpu_usage": 85.0, "latency_ms": [200, 500, 1200]}})

    @field_validator("logs")
    @classmethod
    def bound_logs(cls, value):
        if len(value) > 2000 or sum(map(len, value)) > 100000 or any(len(line)>4000 for line in value):
            raise ValueError("Logs exceed 2000 entries, 100000 total characters, or 4000 characters per line")
        return value

    @field_validator("metrics")
    @classmethod
    def numeric_metrics(cls, value):
        if len(value) > 100:
            raise ValueError("At most 100 metrics are supported")
        for name, samples in value.items():
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]{0,127}", name):
                raise ValueError("Metric names must contain 1–128 characters")
            values = samples if isinstance(samples, list) else [samples]
            if not values or len(values) > 10000:
                raise ValueError("Metric series must contain 1–10000 samples")
            if any(isinstance(v, bool) or not isinstance(v, (int, float)) or abs(v) > 1e100 or not math.isfinite(v) for v in values):
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
    is_safe: bool = False
    action_type: Literal["read_only", "potentially_disruptive", "configuration_change"] = "read_only"
    priority: str = "High"

class PostmortemArtifacts(BaseModel):
    logs_result: Optional[LogAnalysisResult] = None
    metrics_result: Optional[MetricsAnalysisResult] = None

class ReportContent(BaseModel):
    investigation: Optional[Investigation] = None
    summary_html: str = ""
    summary: str
    root_cause: RootCause
    recommendations: List[Recommendation]
    generated_at: datetime
    engine_version: Optional[str] = None
    artifacts: Optional[PostmortemArtifacts] = None

# --- Job Status Model ---

class JobStatus(BaseModel):
    error: Optional[str] = None
    job_id: UUID
    status: str  # initializing, processing, completed, failed
    step: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    description: Optional[str] = None
    result: Optional[ReportContent] = None


class AnalyzeResponse(JobStatus):
    plan: dict = Field(default_factory=dict)
    root_cause: Optional[RootCause] = None
    recommendations: List[Recommendation] = Field(default_factory=list)
    report: Optional[ReportContent] = None
