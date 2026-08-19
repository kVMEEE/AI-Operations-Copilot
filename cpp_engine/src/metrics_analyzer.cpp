#include "metrics_analyzer.hpp"
#include <cmath>
#include <numeric>
#include <algorithm>
#include <sstream>
#include <iomanip>

namespace aiops {

MetricsAnalyzer::MetricsAnalyzer() {
    // Default baseline thresholds
    default_thresholds_ = {
        {"cpu_usage", 80.0},
        {"cpu_percent", 80.0},
        {"memory_usage", 85.0},
        {"memory_percent", 85.0},
        {"latency_ms", 1000.0},
        {"p99_latency_ms", 1500.0},
        {"error_rate", 0.05},
        {"disk_usage_percent", 90.0},
        {"db_connections", 100.0},
        {"network_drop_rate", 0.02}
    };

    metric_units_ = {
        {"cpu_usage", "%"},
        {"cpu_percent", "%"},
        {"memory_usage", "%"},
        {"memory_percent", "%"},
        {"latency_ms", "ms"},
        {"p99_latency_ms", "ms"},
        {"error_rate", "% (ratio)"},
        {"disk_usage_percent", "%"},
        {"db_connections", " connections"},
        {"network_drop_rate", " ratio"}
    };
}

void MetricsAnalyzer::set_threshold(const std::string& metric_name, double threshold) {
    default_thresholds_[metric_name] = threshold;
}

MetricsAnalysisResult MetricsAnalyzer::analyze(const std::map<std::string, std::vector<double>>& metrics_series) {
    MetricsAnalysisResult result;
    result.total_metrics_evaluated = static_cast<int>(metrics_series.size());

    for (const auto& [name, series] : metrics_series) {
        if (series.empty()) continue;

        double max_val = *std::max_element(series.begin(), series.end());
        double last_val = series.back();
        
        // Calculate Mean and Standard Deviation
        double sum = std::accumulate(series.begin(), series.end(), 0.0);
        double mean = sum / series.size();

        double sq_sum = 0.0;
        for (double v : series) {
            sq_sum += (v - mean) * (v - mean);
        }
        double stdev = std::sqrt(sq_sum / series.size());

        // Calculate Z-Score of the peak
        double z_score = (stdev > 0.0001) ? ((max_val - mean) / stdev) : 0.0;

        // Lookup threshold
        double threshold = 0.0;
        auto it = default_thresholds_.find(name);
        if (it != default_thresholds_.end()) {
            threshold = it->second;
        } else {
            // If unknown metric, use statistical 3-sigma or 1.5x mean
            threshold = mean + (2.5 * stdev);
            if (threshold <= 0.0) threshold = mean * 1.5;
        }

        bool is_anomaly = (max_val > threshold) || (series.size() > 3 && z_score >= 2.5);

        if (is_anomaly) {
            MetricAnomaly anomaly;
            anomaly.metric_name = name;
            anomaly.current_value = last_val;
            anomaly.peak_value = max_val;
            anomaly.threshold = threshold;
            anomaly.z_score = z_score;

            // Severity determination
            double breach_ratio = (threshold > 0) ? (max_val / threshold) : 1.0;
            if (breach_ratio >= 1.5 || z_score >= 4.0) {
                anomaly.severity = "Critical";
                result.has_critical_anomaly = true;
            } else if (breach_ratio >= 1.1 || z_score >= 2.5) {
                anomaly.severity = "High";
            } else {
                anomaly.severity = "Medium";
            }

            std::string unit = metric_units_.count(name) ? metric_units_[name] : "";
            std::ostringstream oss;
            oss << "Metric '" << name << "' reached peak " << std::fixed << std::setprecision(1) << max_val << unit
                << " (threshold: " << threshold << unit << ", Z-score: " << std::setprecision(2) << z_score << ")";
            anomaly.description = oss.str();

            result.anomalies.push_back(anomaly);
        }
    }

    // Sort anomalies by severity: Critical > High > Medium
    std::sort(result.anomalies.begin(), result.anomalies.end(), [](const MetricAnomaly& a, const MetricAnomaly& b) {
        auto score = [](const std::string& s) {
            if (s == "Critical") return 3;
            if (s == "High") return 2;
            if (s == "Medium") return 1;
            return 0;
        };
        return score(a.severity) > score(b.severity);
    });

    return result;
}

} // namespace aiops
