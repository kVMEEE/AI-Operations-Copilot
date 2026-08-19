import os
import sys
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')

from app.schemas.incident import IncidentCreate
from app.core.workflow import planner
from app.core.cpp_bridge import cpp_bridge

async def test_full_workflow():
    print("================================================================")
    print(f"Testing End-to-End Workflow with C++ Core ({cpp_bridge.version})")
    print("================================================================")

    # 1. Simulate Incident Payload
    incident = IncidentCreate(
        description="Database Deadlock & High Latency Incident",
        logs=[
            "[2026-08-19 14:02:11] WARN [pool-executor-4] Slow query: SELECT * FROM orders duration=4210ms",
            "[2026-08-19 14:02:15] ERROR [http-nio-8080-exec-12] Database connection timeout: Connection pool exhausted (active=100/100)",
            "[2026-08-19 14:02:18] ERROR [http-nio-8080-exec-19] Deadlock detected in database transaction #9021; query canceled",
            "[2026-08-19 14:02:22] ERROR [http-nio-8080-exec-24] 500 Internal Server Error - Failed to acquire database connection"
        ],
        metrics={
            "cpu_usage": [45.2, 58.1, 91.4, 98.2],
            "db_connections": [45, 80, 100, 100],
            "latency_ms": [140, 220, 2800, 4100],
            "error_rate": [0.001, 0.005, 0.18, 0.35]
        }
    )

    # 2. Trigger async workflow
    job_id = await planner.start_analysis(incident)
    print(f"[Workflow] Dispatched Job ID: {job_id}")

    # 3. Wait for workflow completion
    max_wait = 15
    completed = False
    for sec in range(max_wait):
        await asyncio.sleep(0.5)
        status = planner.get_status(job_id)
        print(f"  Step -> [{status.step}] | Status -> [{status.status}]")
        if status.status == "completed":
            completed = True
            break
        elif status.status == "failed":
            raise RuntimeError(f"Workflow failed at step: {status.step}")

    assert completed, "Workflow did not complete within expected time"
    final_status = planner.get_status(job_id)
    assert final_status.result is not None
    assert final_status.result.root_cause is not None
    assert "Database" in final_status.result.root_cause.cause
    assert len(final_status.result.recommendations) > 0

    print("\n[SUCCESS] Generated Postmortem Post:")
    print("----------------------------------------------------------------")
    print(final_status.result.summary[:600] + "...\n[Report truncated for display]")
    print("----------------------------------------------------------------")
    print(">>> E2E WORKFLOW TEST PASSED! <<<")

if __name__ == "__main__":
    asyncio.run(test_full_workflow())
