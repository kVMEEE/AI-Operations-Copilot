from typing import Dict, Any, List
from app.schemas.incident import MetricsAnalysisResult, MetricAnomaly

class MetricsAnalysisAgent:
    def __init__(self):
        # Define simple thresholds for demonstration
        self.thresholds = {
            "cpu_usage": 80.0,
            "memory_usage": 85.0,
            "latency_ms": 1000.0,
            "error_rate": 0.05
        }

    def analyze(self, metrics: Dict[str, Any]) -> MetricsAnalysisResult:
        anomalies = []

        for metric_name, value in metrics.items():
            # Handle list of values (time series) - take max for simplicity
            current_val = value
            if isinstance(value, list):
                current_val = max([float(v) for v in value]) if value else 0
            else:
                try:
                    current_val = float(value)
                except (ValueError, TypeError):
                    continue # Skip non-numeric

            threshold = self.thresholds.get(metric_name)
            if threshold and current_val > threshold:
                anomalies.append(MetricAnomaly(
                    metric_name=metric_name,
                    value=current_val,
                    threshold=threshold,
                    description=f"Metric {metric_name} ({current_val}) exceeded threshold ({threshold})"
                ))

        return MetricsAnalysisResult(anomalies=anomalies)
