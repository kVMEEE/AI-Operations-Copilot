from typing import List, Optional
from app.schemas.incident import RootCause, LogAnalysisResult, MetricsAnalysisResult

class RootCauseAgent:
    def analyze(self, logs_result: LogAnalysisResult, metrics_result: MetricsAnalysisResult) -> RootCause:
        # Heuristic Correlation
        
        # Check for DB issues
        db_logs = any("Database" in p.pattern for p in logs_result.patterns)
        high_latency = any("latency" in a.metric_name for a in metrics_result.anomalies)
        
        if db_logs and high_latency:
            return RootCause(
                cause="Database Saturation",
                confidence_score=0.85,
                reasoning="Detected 'Database' related error logs coinciding with high latency metrics."
            )
            
        # Check for Network issues
        network_logs = any("Network" in p.pattern or "Timeout" in p.pattern for p in logs_result.patterns)
        if network_logs:
             return RootCause(
                cause="Network Connectivity Issue",
                confidence_score=0.75,
                reasoning="Frequent network timeouts detected in logs."
            )
            
        # Check for Resource Exhaustion
        oom_logs = any("OOM" in p.pattern for p in logs_result.patterns)
        high_mem = any("memory" in a.metric_name for a in metrics_result.anomalies)
        
        if oom_logs or high_mem:
             return RootCause(
                cause="Memory Exhaustion",
                confidence_score=0.90,
                reasoning="Out of Memory errors or high memory usage metrics detected."
             )

        # Default
        return RootCause(
            cause="Unknown Anomaly",
            confidence_score=0.3,
            reasoning="No strong correlation found between logs and metrics."
        )
