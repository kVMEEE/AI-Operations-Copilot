from app.agents.base import BaseAgent

class PlannerAgent(BaseAgent):

    def run(self, input_data: dict) -> dict:
        """
        Decide which agents should be triggered
        based on available inputs.
        """

        tasks = []

        if "logs" in input_data and input_data["logs"]:
            tasks.append("log_analysis")

        if "metrics" in input_data and input_data["metrics"]:
            tasks.append("metrics_analysis")

        return {
            "tasks": tasks,
            "reason": "Planned based on input payload"
        }
