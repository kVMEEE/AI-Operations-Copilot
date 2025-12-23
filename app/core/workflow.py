import uuid
import asyncio
from typing import Dict
from app.schemas.incident import IncidentCreate, JobStatus, ReportContent
from app.agents.log_analysis import LogAnalysisAgent
from app.agents.metrics_analysis import MetricsAnalysisAgent
from app.agents.root_cause import RootCauseAgent
from app.agents.recommendation import RecommendationAgent
from app.agents.report_generator import ReportGeneratorAgent

# In-memory store
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
        jobs[job_id] = JobStatus(job_id=job_id, status="processing", step="initializing")
        
        # Fire and forget background task
        asyncio.create_task(self.run_workflow(job_id, incident))
        return job_id

    async def run_workflow(self, job_id: str, incident: IncidentCreate):
        try:
            # 1. Log Analysis
            jobs[job_id].step = "analyzing_logs"
            log_result = self.log_agent.analyze(incident.logs)
            await asyncio.sleep(1) # Simulate think time

            # 2. Metrics Analysis
            jobs[job_id].step = "analyzing_metrics"
            metrics_result = self.metrics_agent.analyze(incident.metrics)
            await asyncio.sleep(1)

            # 3. Root Cause Analysis
            jobs[job_id].step = "inferring_root_cause"
            root_cause = self.rc_agent.analyze(log_result, metrics_result)
            await asyncio.sleep(1)

            # 4. Recommendations
            jobs[job_id].step = "generating_recommendations"
            recommendations = self.rec_agent.recommend(root_cause)
            
            # 5. Report Generation
            jobs[job_id].step = "finalizing_report"
            report = self.report_agent.generate(incident.description, root_cause, recommendations)
            
            # Complete
            jobs[job_id].result = report
            jobs[job_id].status = "completed"
            jobs[job_id].step = "done"

        except Exception as e:
            print(f"Job {job_id} failed: {e}")
            jobs[job_id].status = "failed"
            jobs[job_id].step = str(e)

    def get_status(self, job_id: str) -> JobStatus:
        return jobs.get(job_id)

    def get_all_jobs(self) -> Dict[str, JobStatus]:
        return jobs

planner = PlannerAgent()
