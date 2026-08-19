from typing import List
from app.schemas.incident import LogPattern, LogAnalysisResult
from app.core.cpp_bridge import cpp_bridge

class LogAnalysisAgent:
    """
    Log Analysis Agent powered by high-performance C++ pattern detection engine.
    """

    def analyze(self, logs: List[str]) -> LogAnalysisResult:
        if not logs:
            return LogAnalysisResult(patterns=[], total_logs=0, error_count=0, warning_count=0, engine=cpp_bridge.version)

        raw_res = cpp_bridge.analyze_logs(logs)

        patterns = [
            LogPattern(
                pattern=p.get("pattern", "Unknown"),
                frequency=p.get("frequency", 0),
                severity=p.get("severity", "Medium"),
                sample_lines=p.get("sample_lines", [])
            )
            for p in raw_res.get("patterns", [])
        ]

        return LogAnalysisResult(
            patterns=patterns,
            total_logs=raw_res.get("total_logs", len(logs)),
            error_count=raw_res.get("error_count", 0),
            warning_count=raw_res.get("warning_count", 0),
            engine=cpp_bridge.version
        )
