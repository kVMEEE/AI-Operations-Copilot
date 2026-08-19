from typing import Dict, Any
from app.schemas.incident import MetricsAnalysisResult, MetricAnomaly
from app.core.cpp_bridge import cpp_bridge

class MetricsAnalysisAgent:
    """
    Metrics Analysis Agent powered by high-performance C++ statistical anomaly detector.
    """

    def analyze(self, metrics: Dict[str, Any]) -> MetricsAnalysisResult:
        if not metrics:
            return MetricsAnalysisResult(anomalies=[], total_metrics_evaluated=0, has_critical_anomaly=False, engine=cpp_bridge.version)

        raw_res = cpp_bridge.analyze_metrics(metrics)

        anomalies = [
            MetricAnomaly(
                metric_name=a.get("metric_name", "unknown"),
                timestamp=a.get("timestamp"),
                value=float(a.get("value", 0.0)),
                peak_value=float(a.get("peak_value", a.get("value", 0.0))),
                threshold=float(a.get("threshold", 0.0)),
                z_score=float(a.get("z_score", 0.0)),
                severity=a.get("severity", "High"),
                description=a.get("description", "")
            )
            for a in raw_res.get("anomalies", [])
        ]

        return MetricsAnalysisResult(
            anomalies=anomalies,
            total_metrics_evaluated=raw_res.get("total_metrics_evaluated", len(metrics)),
            has_critical_anomaly=raw_res.get("has_critical_anomaly", False),
            engine=cpp_bridge.version
        )
