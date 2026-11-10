from datetime import datetime
from app.schemas.incident import ReportContent, RootCause, Recommendation, LogAnalysisResult, MetricsAnalysisResult, PostmortemArtifacts
from typing import List, Optional

class ReportGeneratorAgent:
    """
    Incident Report Generator Agent producing clean, executive & technical postmortem reports.
    """

    def generate(
        self,
        incident_desc: str,
        root_cause: RootCause,
        recommendations: List[Recommendation],
        logs_result: Optional[LogAnalysisResult] = None,
        metrics_result: Optional[MetricsAnalysisResult] = None,
        engine_version: Optional[str] = None
    ) -> ReportContent:
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        md = []
        md.append(f"# 🚨 Incident Postmortem Report: {incident_desc}")
        md.append("")
        md.append(f"- **Generated At**: `{now_str}`")
        md.append(f"- **Engine**: `{engine_version or 'C++17 Native Analytics'}`")
        md.append(f"- **Status**: `ANALYSIS_COMPLETED`")
        md.append("")
        md.append("---")
        md.append("")
        md.append("## 1. Executive Summary")
        md.append(f"> [!IMPORTANT]")
        md.append(f"> **Identified Cause**: **{root_cause.cause}** (Heuristic score: **{root_cause.confidence_score:.2f}**, not a calibrated probability)")
        md.append(f">")
        md.append(f"> **Reasoning**: {root_cause.reasoning}")
        md.append("")

        if root_cause.contributing_factors:
            md.append("### Key Contributing Factors")
            for factor in root_cause.contributing_factors:
                md.append(f"- ⚠️ {factor}")
            md.append("")

        md.append("---")
        md.append("")
        md.append("## 2. Telemetry & Analytics Findings")
        
        if logs_result and logs_result.patterns:
            md.append("### Log Pattern Detection (C++ Engine)")
            md.append("| Pattern Signature | Frequency | Severity |")
            md.append("| :--- | :--- | :--- |")
            for p in logs_result.patterns:
                md.append(f"| `{p.pattern}` | **{p.frequency}** | `{p.severity}` |")
            md.append("")

        if metrics_result and metrics_result.anomalies:
            md.append("### Metric Anomalies (C++ Statistical Detector)")
            md.append("| Metric | Peak Value | Threshold | Z-Score | Severity |")
            md.append("| :--- | :--- | :--- | :--- | :--- |")
            for a in metrics_result.anomalies:
                md.append(f"| `{a.metric_name}` | **{a.peak_value:.1f}** | {a.threshold:.1f} | {a.z_score:.2f}σ | `{a.severity}` |")
            md.append("")

        md.append("---")
        md.append("")
        md.append("## 3. Suggested Actions for Human Review")
        md.append("> [!NOTE]")
        md.append("> Actions require operator review; some may affect workloads. No remediation was executed.")
        md.append("")
        for idx, rec in enumerate(recommendations, 1):
            md.append(f"### {idx}. {rec.action} `[{rec.priority}]`")
            md.append(f"{rec.description}")
            md.append("")

        md.append("---")
        md.append("> Generated autonomously by **AI Operations Copilot (C++ & Python Edition)**.")

        full_md = "\n".join(md)

        artifacts = PostmortemArtifacts(
            logs_result=logs_result,
            metrics_result=metrics_result
        )

        return ReportContent(
            summary=full_md,
            root_cause=root_cause,
            recommendations=recommendations,
            generated_at=datetime.now(),
            engine_version=engine_version,
            artifacts=artifacts
        )
