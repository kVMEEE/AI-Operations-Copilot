#include "correlator.hpp"
#include <sstream>
#include <iomanip>

namespace aiops {

CorrelatedRootCause Correlator::correlate(const LogAnalysisResult& logs, const MetricsAnalysisResult& metrics) {
    CorrelatedRootCause rc;

    bool has_db_logs = false;
    bool has_oom_logs = false;
    bool has_net_logs = false;
    bool has_server_err_logs = false;
    bool has_disk_logs = false;
    bool has_thread_logs = false;

    for (const auto& p : logs.patterns) {
        if (p.pattern_name.find("Database") != std::string::npos) has_db_logs = true;
        if (p.pattern_name.find("OOM") != std::string::npos) has_oom_logs = true;
        if (p.pattern_name.find("Network") != std::string::npos) has_net_logs = true;
        if (p.pattern_name.find("Server Error") != std::string::npos) has_server_err_logs = true;
        if (p.pattern_name.find("Disk") != std::string::npos) has_disk_logs = true;
        if (p.pattern_name.find("Thread") != std::string::npos) has_thread_logs = true;
    }

    bool high_latency = false;
    bool high_cpu = false;
    bool high_mem = false;
    bool high_err = false;
    bool high_disk = false;
    bool high_net_drop = false;

    for (const auto& a : metrics.anomalies) {
        if (a.metric_name.find("latency") != std::string::npos) high_latency = true;
        if (a.metric_name.find("cpu") != std::string::npos) high_cpu = true;
        if (a.metric_name.find("memory") != std::string::npos) high_mem = true;
        if (a.metric_name.find("error") != std::string::npos) high_err = true;
        if (a.metric_name.find("disk") != std::string::npos) high_disk = true;
        if (a.metric_name.find("network") != std::string::npos) high_net_drop = true;
    }

    std::ostringstream reasons;

    // Rule 1: Memory Exhaustion / OOM
    if (has_oom_logs || (high_mem && (has_server_err_logs || high_latency))) {
        rc.cause = "Memory Exhaustion & OOM Cascade";
        rc.primary_category = "Memory";
        rc.confidence_score = has_oom_logs ? 0.95 : 0.82;
        reasons << "Process memory breached critical limits";
        if (has_oom_logs) reasons << " triggering active OutOfMemoryError crashes";
        if (high_mem) reasons << " with memory utilization anomalies detected in metrics telemetry";
        reasons << ".";
        rc.reasoning = reasons.str();
        if (has_oom_logs) rc.contributing_factors.push_back("OOM log patterns detected");
        if (high_mem) rc.contributing_factors.push_back("Memory saturation anomaly");
        return rc;
    }

    // Rule 2: Database Saturation & Deadlocks
    if (has_db_logs || (high_latency && high_cpu && has_server_err_logs)) {
        if (has_db_logs && high_latency) {
            rc.cause = "Database Saturation & Lock Contention";
            rc.primary_category = "Database";
            rc.confidence_score = 0.92;
            rc.reasoning = "Database lock/connection exceptions coincided with acute API latency spikes.";
            rc.contributing_factors.push_back("Database connection pool / deadlock logs");
            rc.contributing_factors.push_back("High API latency degradation");
            return rc;
        } else if (has_db_logs) {
            rc.cause = "Database Query & Connection Degradation";
            rc.primary_category = "Database";
            rc.confidence_score = 0.85;
            rc.reasoning = "Database error signatures identified during operational period.";
            rc.contributing_factors.push_back("Database error log signatures");
            return rc;
        }
    }

    // Rule 3: Network Partition / Upstream Timeout
    if (has_net_logs || (high_net_drop && (high_latency || has_server_err_logs))) {
        rc.cause = "Upstream Network Latency / Dependency Timeout";
        rc.primary_category = "Network";
        rc.confidence_score = (has_net_logs && high_latency) ? 0.89 : 0.78;
        rc.reasoning = "Upstream connection timeouts and network socket degradation coincided with service error rate increases.";
        if (has_net_logs) rc.contributing_factors.push_back("Network timeout log events");
        if (high_net_drop) rc.contributing_factors.push_back("Packet/socket drops in telemetry");
        return rc;
    }

    // Rule 4: Disk Exhaustion
    if (has_disk_logs || high_disk) {
        rc.cause = "Disk Volume Space Exhaustion";
        rc.primary_category = "Disk";
        rc.confidence_score = 0.94;
        rc.reasoning = "Local disk volume utilization reached 100% capacity preventing write operations.";
        if (has_disk_logs) rc.contributing_factors.push_back("Disk write failure logs");
        if (high_disk) rc.contributing_factors.push_back("Disk utilization metric threshold breach");
        return rc;
    }

    // Rule 5: CPU Starvation / Thread Pool Exhaustion
    if (high_cpu || has_thread_logs) {
        rc.cause = "CPU & Thread Pool Starvation";
        rc.primary_category = "CPU";
        rc.confidence_score = (high_cpu && has_thread_logs) ? 0.88 : 0.74;
        rc.reasoning = "Excessive CPU load caused thread queue backlog and request queue latency.";
        if (high_cpu) rc.contributing_factors.push_back("High CPU utilization anomaly");
        if (has_thread_logs) rc.contributing_factors.push_back("Thread pool rejection logs");
        return rc;
    }

    // Fallback: Generic Uncorrelated Anomaly
    if (logs.error_count > 0 || !metrics.anomalies.empty()) {
        rc.cause = "Uncorrelated System Anomaly";
        rc.primary_category = "Unknown";
        rc.confidence_score = 0.45;
        rc.reasoning = "Isolated error logs or metrics fluctuations detected without strong cross-correlation signatures.";
        if (logs.error_count > 0) rc.contributing_factors.push_back("General error logs found");
        if (!metrics.anomalies.empty()) rc.contributing_factors.push_back("Isolated metric threshold breaches");
        return rc;
    }

    rc.cause = "Nominal System Health / Transient Jitter";
    rc.primary_category = "None";
    rc.confidence_score = 0.20;
    rc.reasoning = "No critical error patterns or anomalous metric thresholds were breached.";
    return rc;
}

} // namespace aiops
