from app.agents.planner import PlannerAgent
from app.agents.log_analysis import LogAnalysisAgent

class AgentRunner:

    def __init__(self):
        self.planner = PlannerAgent()
        self.agents = {
            "log_analysis": LogAnalysisAgent()
        }

    def run(self, payload: dict) -> dict:
        plan = self.planner.run(payload)

        results = []

        for task in plan["tasks"]:
            agent = self.agents.get(task)
            if agent:
                result = agent.run(payload)
                results.append(result)

        return {
            "plan": plan,
            "results": results
        }
