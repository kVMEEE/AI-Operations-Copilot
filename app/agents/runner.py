"""Compatibility adapter to the shared investigation service."""
from app.core.workflow import planner
from app.schemas.incident import IncidentCreate
class AgentRunner:
    async def run(self,payload):
        return await planner.analyze(IncidentCreate.model_validate(payload))
