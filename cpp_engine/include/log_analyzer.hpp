#ifndef LOG_ANALYZER_HPP
#define LOG_ANALYZER_HPP

#include <string>
#include <vector>
#include <map>
#include <regex>

namespace aiops {

struct PatternMatch {
    std::string pattern_name;
    int frequency = 0;
    std::string severity; // High, Medium, Low, Critical
    std::vector<std::string> sample_lines;
};

struct LogAnalysisResult {
    std::vector<PatternMatch> patterns;
    int total_logs = 0;
    int error_count = 0;
    int warning_count = 0;
};

class LogAnalyzer {
public:
    LogAnalyzer();
    ~LogAnalyzer() = default;

    LogAnalysisResult analyze(const std::vector<std::string>& log_lines);

private:
    struct Rule {
        std::string name;
        std::regex regex_pattern;
        std::string severity;
    };

    std::vector<Rule> rules_;
};

} // namespace aiops

#endif // LOG_ANALYZER_HPP
