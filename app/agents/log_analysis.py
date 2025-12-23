import re
from typing import List
from app.schemas.incident import LogPattern, LogAnalysisResult

class LogAnalysisAgent:
    def __init__(self):
        self.common_patterns = [
            (r"Connection timed out", "Network Timeout"),
            (r"500 Internal Server Error", "Server Error"),
            (r"Deadlock detected", "Database Deadlock"),
            (r"OutOfMemoryError", "OOM Crash"),
        ]

    def analyze(self, logs: List[str]) -> LogAnalysisResult:
        patterns_found = {}
        
        for log in logs:
            matched = False
            for pattern_regex, label in self.common_patterns:
                if re.search(pattern_regex, log, re.IGNORECASE):
                    if label not in patterns_found:
                        patterns_found[label] = {"count": 0, "severity": "High"}
                    patterns_found[label]["count"] += 1
                    matched = True
                    break
            
            # Simple fallback for unknown errors
            if not matched and "error" in log.lower():
                label = "Generic Error"
                if label not in patterns_found:
                    patterns_found[label] = {"count": 0, "severity": "Medium"}
                patterns_found[label]["count"] += 1

        results = []
        for label, data in patterns_found.items():
            results.append(LogPattern(
                pattern=label,
                frequency=data["count"],
                severity=data["severity"]
            ))

        return LogAnalysisResult(
            patterns=results,
            total_logs=len(logs)
        )
