from typing import List, Optional
from app.schemas.incident import RootCause, LogAnalysisResult, MetricsAnalysisResult
from app.core.cpp_bridge import cpp_bridge

class RootCauseAgent:
    """
    Root Cause Analysis Agent correlating log patterns and metric spikes using C++ heuristics.
    """

    def analyze(self, logs_result: LogAnalysisResult, metrics_result: MetricsAnalysisResult, raw_logs: Optional[List[str]] = None, raw_metrics: Optional[dict] = None) -> RootCause:
        # If raw logs/metrics are provided, run native C++ Correlator
        if raw_logs is not None and raw_metrics is not None:
            correlate_res = cpp_bridge.correlate(raw_logs, raw_metrics)
            return RootCause(
                cause=correlate_res.get("cause", "Unknown System Anomaly"),
                confidence_score=float(correlate_res.get("confidence_score", 0.5)),
                reasoning=correlate_res.get("reasoning", "Correlation generated from telemetry."),
                primary_category=correlate_res.get("primary_category", "Unknown"),
                contributing_factors=correlate_res.get("contributing_factors", []),
                engine=cpp_bridge.version
            )

        # Fallback cross-agent heuristic
        db_logs = any("Database" in p.pattern for p in logs_result.patterns)
        high_latency = any("latency" in a.metric_name for a in metrics_result.anomalies)
        oom_logs = any("OOM" in p.pattern for p in logs_result.patterns)
        high_mem = any("memory" in a.metric_name for a in metrics_result.anomalies)
        net_logs = any("Network" in p.pattern or "Timeout" in p.pattern for p in logs_result.patterns)

        if oom_logs or high_mem:
            return RootCause(
                cause="Memory Exhaustion & OOM Cascade",
                confidence_score=0.95 if oom_logs else 0.85,
                reasoning="Process memory breached critical limits, triggering active OOM kills or high allocation pressure.",
                primary_category="Memory",
                contributing_factors=["OOM log signatures", "High memory telemetry"],
                engine=cpp_bridge.version
            )

        if db_logs and high_latency:
            return RootCause(
                cause="Database Saturation & Lock Contention",
                confidence_score=0.92,
                reasoning="Database connection pool exhaustion and lock timeouts coincided with API latency spikes.",
                primary_category="Database",
                contributing_factors=["Database lock/timeout logs", "API latency spike"],
                engine=cpp_bridge.version
            )

        if net_logs:
            return RootCause(
                cause="Upstream Network Latency / Dependency Timeout",
                confidence_score=0.82,
                reasoning="Frequent network timeouts detected to upstream downstream dependencies.",
                primary_category="Network",
                contributing_factors=["Network timeout error patterns"],
                engine=cpp_bridge.version
            )

        return RootCause(
            cause="Uncorrelated System Degradation",
            confidence_score=0.40,
            reasoning="Telemetry exhibited anomalies without a single definitive root-cause signature.",
            primary_category="General",
            contributing_factors=["Anomalies detected in telemetry"],
            engine=cpp_bridge.version
        )
