#ifndef CORRELATOR_HPP
#define CORRELATOR_HPP

#include "log_analyzer.hpp"
#include "metrics_analyzer.hpp"
#include <string>
#include <vector>

namespace aiops {

struct CorrelatedRootCause {
    std::string cause;
    double confidence_score = 0.0;
    std::string reasoning;
    std::string primary_category; // Database, Memory, Network, CPU, Disk, Unknown
    std::vector<std::string> contributing_factors;
};

class Correlator {
public:
    Correlator() = default;
    ~Correlator() = default;

    CorrelatedRootCause correlate(const LogAnalysisResult& logs, const MetricsAnalysisResult& metrics);
};

} // namespace aiops

#endif // CORRELATOR_HPP
