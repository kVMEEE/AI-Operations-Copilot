import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.cpp_bridge import cpp_bridge

def test_bridge_status():
    print(f"[TEST] C++ Core Version: {cpp_bridge.version}")
    print(f"[TEST] Native Acceleration Active: {cpp_bridge.is_native}")
    assert cpp_bridge.is_native is True, "C++ Core Library should be loaded natively"

def test_log_analysis():
    logs = [
        "[2026-08-19 12:00:01] ERROR: 500 Internal Server Error - connection reset",
        "[2026-08-19 12:00:02] WARN: Connection timed out to db-replica.internal",
        "[2026-08-19 12:00:03] ERROR: OutOfMemoryError: Java heap space",
        "[2026-08-19 12:00:04] ERROR: 500 Internal Server Error - downstream unreachable"
    ]
    res = cpp_bridge.analyze_logs(logs)
    print("\n[TEST] C++ Log Analysis Output:")
    print(res)
    assert res["total_logs"] == 4
    patterns = {p["pattern"]: p["frequency"] for p in res["patterns"]}
    assert "Server Error 5xx" in patterns
    assert patterns["Server Error 5xx"] == 2
    assert "OOM Crash" in patterns
    assert "Network Timeout" in patterns

def test_metrics_analysis():
    metrics = {
        "cpu_usage": [45.0, 52.0, 92.5, 96.0],
        "memory_usage": 88.0,
        "latency_ms": [120, 150, 2400, 3100],
        "disk_usage_percent": 45.0
    }
    res = cpp_bridge.analyze_metrics(metrics)
    print("\n[TEST] C++ Metrics Analysis Output:")
    print(res)
    anomalies = {a["metric_name"]: a for a in res["anomalies"]}
    assert "cpu_usage" in anomalies
    assert "memory_usage" in anomalies
    assert "latency_ms" in anomalies
    assert "disk_usage_percent" not in anomalies

def test_correlation():
    logs = [
        "ERROR: Deadlock detected in database transaction #4912",
        "ERROR: Connection pool exhausted - database timeout after 30s"
    ]
    metrics = {
        "latency_ms": [200, 450, 3200, 4500],
        "cpu_usage": [40, 55, 91]
    }
    res = cpp_bridge.correlate(logs, metrics)
    print("\n[TEST] C++ Correlation Output:")
    print(res)
    assert "Database" in res["cause"]
    assert res["confidence_score"] >= 0.80

if __name__ == "__main__":
    try:
        test_bridge_status()
        test_log_analysis()
        test_metrics_analysis()
        test_correlation()
        print("\n>>> ALL C++ CORE ENGINE INTEGRATION TESTS PASSED SUCCESSFULLY! <<<")
    except Exception as e:
        print(f"\n[FAILED] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
