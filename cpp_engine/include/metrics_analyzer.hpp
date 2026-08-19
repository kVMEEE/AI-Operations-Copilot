#ifndef METRICS_ANALYZER_HPP
#define METRICS_ANALYZER_HPP

#include <string>
#include <vector>
#include <map>

namespace aiops {

struct MetricAnomaly {
    std::string metric_name;
    double current_value = 0.0;
    double threshold = 0.0;
    double peak_value = 0.0;
    double z_score = 0.0;
    std::string severity; // Critical, High, Medium, Low
    std::string description;
};

struct MetricsAnalysisResult {
    std::vector<MetricAnomaly> anomalies;
    int total_metrics_evaluated = 0;
    bool has_critical_anomaly = false;
};

class MetricsAnalyzer {
public:
    MetricsAnalyzer();
    ~MetricsAnalyzer() = default;

    void set_threshold(const std::string& metric_name, double threshold);
    MetricsAnalysisResult analyze(const std::map<std::string, std::vector<double>>& metrics_series);

private:
    std::map<std::string, double> default_thresholds_;
    std::map<std::string, std::string> metric_units_;
};

} // namespace aiops

#endif // METRICS_ANALYZER_HPP
