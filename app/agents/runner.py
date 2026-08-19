from app.agents.planner import PlannerAgent
from app.agents.log_analysis import LogAnalysisAgent
from app.agents.metrics_analysis import MetricsAnalysisAgent
from app.agents.root_cause import RootCauseAgent
from app.agents.recommendation import RecommendationAgent
from app.agents.report_generator import ReportGeneratorAgent

class AgentRunner:
    def __init__(self):
        self.planner = PlannerAgent()
        self.log_agent = LogAnalysisAgent()
        self.metrics_agent = MetricsAnalysisAgent()
        self.rc_agent = RootCauseAgent()
        self.rec_agent = RecommendationAgent()
        self.report_agent = ReportGeneratorAgent()

    def run(self, payload: dict) -> dict:
        plan = self.planner.run(payload)
        logs = payload.get("logs", [])
        metrics = payload.get("metrics", {})
        description = payload.get("description", "Incident Analysis")

        log_res = self.log_agent.analyze(logs) if "log_analysis" in plan["tasks"] else None
        metrics_res = self.metrics_agent.analyze(metrics) if "metrics_analysis" in plan["tasks"] else None

        rc = self.rc_agent.analyze(log_res, metrics_res, raw_logs=logs, raw_metrics=metrics)
        recommendations = self.rec_agent.recommend(rc)
        report = self.report_agent.generate(description, rc, recommendations, log_res, metrics_res)

        return {
            "plan": plan,
            "root_cause": rc.dict(),
            "recommendations": [r.dict() for r in recommendations],
            "report": report.dict()
        }
