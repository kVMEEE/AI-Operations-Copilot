from typing import List
from app.schemas.incident import Recommendation, RootCause

class RecommendationAgent:
    def recommend(self, root_cause: RootCause) -> List[Recommendation]:
        recommendations = []
        
        cause = root_cause.cause.lower()
        
        if "database" in cause:
            recommendations.append(Recommendation(
                action="Check Active Queries",
                description="Run 'SELECT * FROM pg_stat_activity' to find long-running queries.",
                is_safe=True
            ))
            recommendations.append(Recommendation(
                action="Check Connection Pool",
                description="Verify if the application connection pool has reached max_size.",
                is_safe=True
            ))
            
        elif "network" in cause:
             recommendations.append(Recommendation(
                action="Verify Firewall Rules",
                description="Check if any recent firewall changes blocked traffic.",
                is_safe=True
            ))
             recommendations.append(Recommendation(
                action="Check Dependency Health",
                description="Ping downstream services to verify availability.",
                is_safe=True
            ))
            
        elif "memory" in cause:
             recommendations.append(Recommendation(
                action="Analyze Heap Dump",
                description="Capture and analyze a heap dump to identify memory leaks.",
                is_safe=True
            ))
             recommendations.append(Recommendation(
                action="Scale Up",
                description="Consider increasing memory allocation for the container (requires restart).",
                is_safe=True
            ))
            
        else:
            recommendations.append(Recommendation(
                action="Investigate Application Logs",
                description="Manually review logs for unhandled exceptions.",
                is_safe=True
            ))

        return recommendations
