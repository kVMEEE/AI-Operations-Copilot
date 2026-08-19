from typing import List
from app.schemas.incident import Recommendation, RootCause

class RecommendationAgent:
    """
    Recommendation Agent generating safe, actionable remediation steps.
    Strictly read-only / diagnostic actions.
    """

    def recommend(self, root_cause: RootCause) -> List[Recommendation]:
        recommendations = []
        cause = root_cause.cause.lower()
        cat = (root_cause.primary_category or "").lower()

        if "database" in cause or cat == "database":
            recommendations.append(Recommendation(
                action="Inspect Active & Blocking Queries",
                description="Run 'SELECT pid, query, state, age(clock_timestamp(), query_start) FROM pg_stat_activity WHERE state != 'idle' ORDER BY age DESC;' to spot hung transactions.",
                is_safe=True,
                priority="Critical"
            ))
            recommendations.append(Recommendation(
                action="Verify Database Connection Pool Limits",
                description="Check if service connection pool has hit max_connections or if client leaked open sessions.",
                is_safe=True,
                priority="High"
            ))
            recommendations.append(Recommendation(
                action="Check Index Usage on Slow Tables",
                description="Review database query plan (EXPLAIN ANALYZE) for sequential table scans on recent queries.",
                is_safe=True,
                priority="Medium"
            ))

        elif "memory" in cause or "oom" in cause or cat == "memory":
            recommendations.append(Recommendation(
                action="Capture & Inspect Process Heap Dump",
                description="Capture a lightweight heap dump or profiling snapshot (e.g. py-spy / jcmd) before restarting the worker.",
                is_safe=True,
                priority="Critical"
            ))
            recommendations.append(Recommendation(
                action="Audit In-Memory Caches & Buffer Sizes",
                description="Verify if local LRU cache size limits or unbounded queue buffers are growing without eviction.",
                is_safe=True,
                priority="High"
            ))
            recommendations.append(Recommendation(
                action="Evaluate Container Memory Limits (Cgroups)",
                description="Review Kubernetes/container memory limits (OOMScoreAdjust) and consider scaling horizontal replicas.",
                is_safe=True,
                priority="Medium"
            ))

        elif "network" in cause or "timeout" in cause or cat == "network":
            recommendations.append(Recommendation(
                action="Verify Downstream Dependency Health",
                description="Execute TCP/HTTP health checks on upstream endpoints and DNS resolvers from the worker container.",
                is_safe=True,
                priority="Critical"
            ))
            recommendations.append(Recommendation(
                action="Check Network Security Groups & Firewalls",
                description="Review recent VPC route table updates or firewall rules for unexpected ingress/egress throttling.",
                is_safe=True,
                priority="High"
            ))

        elif "disk" in cause or cat == "disk":
            recommendations.append(Recommendation(
                action="Inspect Disk Usage & Log Rotations",
                description="Run 'df -h' and 'du -sh /var/log/*' to identify unrotated debug log files or temporary cache files.",
                is_safe=True,
                priority="Critical"
            ))
            recommendations.append(Recommendation(
                action="Enable Automated Log Retention Policies",
                description="Configure logrotate or container stdout streaming to avoid local disk writes.",
                is_safe=True,
                priority="Medium"
            ))

        else:
            recommendations.append(Recommendation(
                action="Review Recent Deployments & Feature Flags",
                description="Check CI/CD deployment logs and recent configuration releases within the incident timeframe.",
                is_safe=True,
                priority="High"
            ))
            recommendations.append(Recommendation(
                action="Examine Unhandled Exception Stack Traces",
                description="Filter application log streams for 5xx responses and panic / unhandled exception traces.",
                is_safe=True,
                priority="Medium"
            ))

        return recommendations
