import uuid
import asyncio
from datetime import datetime
from typing import Dict, Optional
from app.schemas.incident import IncidentCreate, JobStatus, ReportContent
from app.agents.log_analysis import LogAnalysisAgent
from app.agents.metrics_analysis import MetricsAnalysisAgent
from app.agents.root_cause import RootCauseAgent
from app.agents.recommendation import RecommendationAgent
from app.agents.report_generator import ReportGeneratorAgent
from app.core.cpp_bridge import cpp_bridge

# In-memory store for jobs
jobs: Dict[str, JobStatus] = {}

class PlannerAgent:
    def __init__(self):
        self.log_agent = LogAnalysisAgent()
        self.metrics_agent = MetricsAnalysisAgent()
        self.rc_agent = RootCauseAgent()
        self.rec_agent = RecommendationAgent()
        self.report_agent = ReportGeneratorAgent()

    async def start_analysis(self, incident: IncidentCreate) -> str:
        job_id = str(uuid.uuid4())
        job_status = JobStatus(
            job_id=job_id,
            status="processing",
            step="initializing",
            created_at=datetime.utcnow(),
            description=incident.description
        )
        jobs[job_id] = job_status

        # Fire and forget background task
        asyncio.create_task(self.run_workflow(job_id, incident))
        return job_id

    async def run_workflow(self, job_id: str, incident: IncidentCreate):
        try:
            # 1. C++ High-Speed Log Analysis
            jobs[job_id].step = "analyzing_logs"
            await asyncio.sleep(0.5) # Allow UI to display step transition
            log_result = self.log_agent.analyze(incident.logs)

            # 2. C++ Statistical Metrics Anomaly Detection
            jobs[job_id].step = "analyzing_metrics"
            await asyncio.sleep(0.5)
            metrics_result = self.metrics_agent.analyze(incident.metrics)

            # 3. C++ Heuristic Root Cause Correlation
            jobs[job_id].step = "inferring_root_cause"
            await asyncio.sleep(0.5)
            root_cause = self.rc_agent.analyze(
                log_result,
                metrics_result,
                raw_logs=incident.logs,
                raw_metrics=incident.metrics
            )

            # 4. Safe Action Recommendations
            jobs[job_id].step = "generating_recommendations"
            await asyncio.sleep(0.5)
            recommendations = self.rec_agent.recommend(root_cause)

            # 5. Postmortem Markdown Report Generation
            jobs[job_id].step = "finalizing_report"
            await asyncio.sleep(0.5)
            report = self.report_agent.generate(
                incident.description,
                root_cause,
                recommendations,
                logs_result=log_result,
                metrics_result=metrics_result,
                engine_version=cpp_bridge.version
            )

            # Mark Completed
            jobs[job_id].result = report
            jobs[job_id].status = "completed"
            jobs[job_id].step = "done"

        except Exception as e:
            print(f"[Workflow] Error processing job {job_id}: {e}")
            import traceback
            traceback.print_exc()
            jobs[job_id].status = "failed"
            jobs[job_id].step = f"Error: {str(e)}"

    def get_status(self, job_id: str) -> Optional[JobStatus]:
        return jobs.get(job_id)

    def get_all_jobs(self) -> Dict[str, JobStatus]:
        return jobs

planner = PlannerAgent()
