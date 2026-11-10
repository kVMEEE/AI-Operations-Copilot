import os
import sys
import json
import ctypes
from typing import List, Dict, Any, Optional

class CppEngineBridge:
    """
    Python ctypes bridge to the native C++ AI Operations Copilot Core Engine (aiops_core.dll / .so).
    High-performance native analytics with automated pure-Python fallback.
    """

    def __init__(self):
        self._lib = None
        self._is_native = False
        self._version = "Pure Python Fallback Engine"
        self._init_library()

    def _init_library(self):
        # Search candidate paths for the compiled shared library
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # app directory
        root_dir = os.path.dirname(base_dir) # repo root
        
        candidates = [
            os.path.join(base_dir, "lib", "aiops_core.dll"),
            os.path.join(root_dir, "cpp_engine", "build", "aiops_core.dll"),
            os.path.join(base_dir, "lib", "libaiops_core.so"),
            os.path.join(base_dir, "lib", "libaiops_core.dylib"),
            "aiops_core.dll"
        ]

        if sys.platform != "win32":
            candidates = [p for p in candidates if not p.endswith(".dll")]
        for path in candidates:
            if os.path.exists(path):
                try:
                    dll_dir = os.path.dirname(os.path.abspath(path))
                    if hasattr(os, "add_dll_directory") and sys.platform == "win32":
                        try:
                            os.add_dll_directory(dll_dir)
                        except Exception:
                            pass
                    self._lib = ctypes.CDLL(path)
                    self._setup_bindings()
                    self._is_native = True
                    raw_ver = self._lib.aiops_get_version()
                    self._version = raw_ver.decode("utf-8") if isinstance(raw_ver, bytes) else str(raw_ver)
                    print(f"[CppEngineBridge] Loaded native C++ Core: {self._version} from {path}")
                    return
                except Exception as e:
                    print(f"[CppEngineBridge] Warning: Found {path} but failed to load: {e}")

        print("[CppEngineBridge] Notice: Native C++ library not found or loaded yet. Using Python fallback.")

    def _setup_bindings(self):
        # aiops_get_version (returns static const char*)
        self._lib.aiops_get_version.restype = ctypes.c_char_p
        self._lib.aiops_get_version.argtypes = []

        # aiops_analyze_logs
        self._lib.aiops_analyze_logs.restype = ctypes.c_void_p
        self._lib.aiops_analyze_logs.argtypes = [ctypes.c_char_p]

        # aiops_analyze_metrics
        self._lib.aiops_analyze_metrics.restype = ctypes.c_void_p
        self._lib.aiops_analyze_metrics.argtypes = [ctypes.c_char_p]

        # aiops_correlate
        self._lib.aiops_correlate.restype = ctypes.c_void_p
        self._lib.aiops_correlate.argtypes = [ctypes.c_char_p, ctypes.c_char_p]

        # aiops_free_string
        self._lib.aiops_free_string.restype = None
        self._lib.aiops_free_string.argtypes = [ctypes.c_void_p]

    def analyze_incident(self, logs, metrics):
        if self._is_native and hasattr(self._lib, "aiops_analyze_incident"):
            fn = self._lib.aiops_analyze_incident
            fn.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
            fn.restype = ctypes.c_void_p
            result = json.loads(self._read_and_free_c_str(fn(
                json.dumps(logs, ensure_ascii=False).encode(), json.dumps(metrics).encode())))
            return result, "native"
        from app.investigation.analytics import fallback
        return fallback(logs, metrics), "python_fallback"

    def _read_and_free_c_str(self, ptr: Optional[int]) -> Optional[str]:
        if not ptr:
            return None
        try:
            val = ctypes.string_at(ptr).decode("utf-8")
            self._lib.aiops_free_string(ptr)
            return val
        except Exception as e:
            print(f"[CppEngineBridge] Error reading C string: {e}")
            return None

    @property
    def is_native(self) -> bool:
        return self._is_native

    @property
    def version(self) -> str:
        return self._version

    def analyze_logs(self, logs: List[str]) -> Dict[str, Any]:
        """
        Analyze logs using C++ LogAnalyzer engine.
        """
        if self._is_native and self._lib:
            try:
                logs_json = json.dumps(logs).encode("utf-8")
                res_ptr = self._lib.aiops_analyze_logs(logs_json)
                res_str = self._read_and_free_c_str(res_ptr)
                if res_str:
                    return json.loads(res_str)
            except Exception as e:
                print(f"[CppEngineBridge] C++ analyze_logs error ({e}), falling back to Python.")

        # Fallback implementation
        return self._fallback_analyze_logs(logs)

    def analyze_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze metrics time-series or point values using C++ MetricsAnalyzer engine.
        """
        if self._is_native and self._lib:
            try:
                metrics_json = json.dumps(metrics).encode("utf-8")
                res_ptr = self._lib.aiops_analyze_metrics(metrics_json)
                res_str = self._read_and_free_c_str(res_ptr)
                if res_str:
                    return json.loads(res_str)
            except Exception as e:
                print(f"[CppEngineBridge] C++ analyze_metrics error ({e}), falling back to Python.")

        # Fallback implementation
        return self._fallback_analyze_metrics(metrics)

    def correlate(self, logs: List[str], metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Correlate logs and metrics using C++ Correlator engine.
        """
        if self._is_native and self._lib:
            try:
                logs_json = json.dumps(logs).encode("utf-8")
                metrics_json = json.dumps(metrics).encode("utf-8")
                res_ptr = self._lib.aiops_correlate(logs_json, metrics_json)
                res_str = self._read_and_free_c_str(res_ptr)
                if res_str:
                    return json.loads(res_str)
            except Exception as e:
                print(f"[CppEngineBridge] C++ correlate error ({e}), falling back to Python.")

        # Fallback implementation
        return self._fallback_correlate(logs, metrics)

    # --- Python Fallback Implementations ---
    def _fallback_analyze_logs(self, logs: List[str]) -> Dict[str, Any]:
        import re
        patterns = {
            "OOM Crash": (r"OutOfMemoryError|oom-killer|out of memory", "Critical"),
            "Database Deadlock": (r"Deadlock detected|deadlock.*transaction", "High"),
            "Database Connection Saturation": (r"Connection pool exhausted|too many connections|database connection timeout", "High"),
            "Network Timeout": (r"Connection timed out|ETIMEDOUT|gateway timeout|network is unreachable", "High"),
            "Server Error 5xx": (r"500 Internal Server Error|502 Bad Gateway|503 Service Unavailable", "High"),
            "Disk Space Exhaustion": (r"No space left on device|disk full", "Critical")
        }
        counts = {}
        for line in logs:
            matched = False
            for name, (regex, sev) in patterns.items():
                if re.search(regex, line, re.IGNORECASE):
                    if name not in counts:
                        counts[name] = {"frequency": 0, "severity": sev}
                    counts[name]["frequency"] += 1
                    matched = True
                    break
            if not matched and "error" in line.lower():
                if "Generic Error" not in counts:
                    counts["Generic Error"] = {"frequency": 0, "severity": "Medium"}
                counts["Generic Error"]["frequency"] += 1

        pattern_list = [{"pattern": k, "frequency": v["frequency"], "severity": v["severity"]} for k, v in counts.items()]
        return {"patterns": pattern_list, "total_logs": len(logs), "error_count": sum(v["frequency"] for v in counts.values())}

    def _fallback_analyze_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        thresholds = {"cpu_usage": 80.0, "memory_usage": 85.0, "latency_ms": 1000.0, "error_rate": 0.05}
        anomalies = []
        for k, v in metrics.items():
            val = max(v) if isinstance(v, list) and v else float(v) if not isinstance(v, list) else 0.0
            thresh = thresholds.get(k, 100.0)
            if val > thresh:
                anomalies.append({
                    "metric_name": k,
                    "value": val,
                    "peak_value": val,
                    "threshold": thresh,
                    "z_score": 3.0,
                    "severity": "Critical" if val > thresh * 1.3 else "High",
                    "description": f"Metric '{k}' ({val}) breached threshold ({thresh})"
                })
        return {"anomalies": anomalies, "total_metrics_evaluated": len(metrics), "has_critical_anomaly": any(a["severity"] == "Critical" for a in anomalies)}

    def _fallback_correlate(self, logs: List[str], metrics: Dict[str, Any]) -> Dict[str, Any]:
        logs_res = self._fallback_analyze_logs(logs)
        metrics_res = self._fallback_analyze_metrics(metrics)
        has_db_logs = any("Database" in p["pattern"] for p in logs_res["patterns"])
        has_oom_logs = any("OOM" in p["pattern"] for p in logs_res["patterns"])
        high_latency = any("latency" in a["metric_name"] for a in metrics_res["anomalies"])
        high_mem = any("memory" in a["metric_name"] for a in metrics_res["anomalies"])

        if has_oom_logs or high_mem:
            return {"cause": "Memory Exhaustion & OOM Cascade", "confidence_score": 0.95, "primary_category": "Memory", "reasoning": "Memory exhaustion detected in logs and telemetry metrics."}
        if has_db_logs and high_latency:
            return {"cause": "Database Saturation & Lock Contention", "confidence_score": 0.92, "primary_category": "Database", "reasoning": "Database locks coincided with high latency."}
        return {"cause": "System Performance Anomaly", "confidence_score": 0.50, "primary_category": "Unknown", "reasoning": "Uncorrelated events detected."}

# Global singleton instance
cpp_bridge = CppEngineBridge()
