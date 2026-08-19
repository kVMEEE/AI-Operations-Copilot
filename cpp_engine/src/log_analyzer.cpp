#include "log_analyzer.hpp"
#include <algorithm>
#include <iostream>

namespace aiops {

LogAnalyzer::LogAnalyzer() {
    // Define robust operational rules for regex log matching
    rules_ = {
        {"OOM Crash", std::regex(R"((OutOfMemoryError|oom-killer|out of memory|killed process.*memory))", std::regex::icase), "Critical"},
        {"Database Deadlock", std::regex(R"((Deadlock detected|deadlock.*transaction|lock wait timeout))", std::regex::icase), "High"},
        {"Database Connection Saturation", std::regex(R"((Connection pool exhausted|too many connections|database connection timeout|pool max_size reached))", std::regex::icase), "High"},
        {"Network Timeout", std::regex(R"((Connection timed out|ETIMEDOUT|upstream request timeout|gateway timeout|connection refused|network is unreachable))", std::regex::icase), "High"},
        {"Server Error 5xx", std::regex(R"((500 Internal Server Error|502 Bad Gateway|503 Service Unavailable|504 Gateway Timeout))", std::regex::icase), "High"},
        {"Disk Space Exhaustion", std::regex(R"((No space left on device|disk full|I/O error.*write))", std::regex::icase), "Critical"},
        {"Authentication & Security Failure", std::regex(R"((Authentication failed|Unauthorized 401|Forbidden 403|Invalid token))", std::regex::icase), "Medium"},
        {"Thread Pool Starvation", std::regex(R"((Thread pool exhausted|RejectedExecutionException|Thread starvation))", std::regex::icase), "High"},
        {"Slow Query Warning", std::regex(R"((Slow query:.*duration|query execution time >))", std::regex::icase), "Medium"},
        {"Application Exception", std::regex(R"((Exception in thread|Unhandled Exception|Traceback \(most recent call last\)|NullPointerException|Fatal error))", std::regex::icase), "High"}
    };
}

LogAnalysisResult LogAnalyzer::analyze(const std::vector<std::string>& log_lines) {
    LogAnalysisResult result;
    result.total_logs = static_cast<int>(log_lines.size());

    std::map<std::string, PatternMatch> matches_map;

    for (const auto& line : log_lines) {
        if (line.empty()) continue;

        bool matched = false;

        // Check against known rules
        for (const auto& rule : rules_) {
            if (std::regex_search(line, rule.regex_pattern)) {
                auto& match = matches_map[rule.name];
                match.pattern_name = rule.name;
                match.severity = rule.severity;
                match.frequency += 1;
                if (match.sample_lines.size() < 3) {
                    match.sample_lines.push_back(line);
                }
                matched = true;

                if (rule.severity == "Critical" || rule.severity == "High") {
                    result.error_count += 1;
                } else {
                    result.warning_count += 1;
                }
                break;
            }
        }

        // Fallback for generic errors if not matched by specific regex
        if (!matched) {
            std::string lower_line = line;
            std::transform(lower_line.begin(), lower_line.end(), lower_line.begin(), ::tolower);

            if (lower_line.find("error") != std::string::npos || lower_line.find("fatal") != std::string::npos) {
                auto& match = matches_map["Generic Error"];
                match.pattern_name = "Generic Error";
                match.severity = "Medium";
                match.frequency += 1;
                if (match.sample_lines.size() < 3) {
                    match.sample_lines.push_back(line);
                }
                result.error_count += 1;
            } else if (lower_line.find("warn") != std::string::npos) {
                result.warning_count += 1;
            }
        }
    }

    for (auto& pair : matches_map) {
        result.patterns.push_back(pair.second);
    }

    // Sort patterns by frequency descending
    std::sort(result.patterns.begin(), result.patterns.end(), [](const PatternMatch& a, const PatternMatch& b) {
        return a.frequency > b.frequency;
    });

    return result;
}

} // namespace aiops
