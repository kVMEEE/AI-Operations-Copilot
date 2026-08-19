#define AIOPS_CORE_EXPORTS
#include "c_api.h"
#include "log_analyzer.hpp"
#include "metrics_analyzer.hpp"
#include "correlator.hpp"

#include <cstring>
#include <string>
#include <vector>
#include <map>
#include <sstream>
#include <iostream>
#include <iomanip>

static std::string escape_json(const std::string& s) {
    std::ostringstream o;
    for (auto c = s.cbegin(); c != s.cend(); ++c) {
        switch (*c) {
        case '"': o << "\\\""; break;
        case '\\': o << "\\\\"; break;
        case '\b': o << "\\b"; break;
        case '\f': o << "\\f"; break;
        case '\n': o << "\\n"; break;
        case '\r': o << "\\r"; break;
        case '\t': o << "\\t"; break;
        default:
            if ('\x00' <= *c && *c <= '\x1f') {
                o << "\\u"
                  << std::hex << std::setw(4) << std::setfill('0') << static_cast<int>(*c);
            } else {
                o << *c;
            }
        }
    }
    return o.str();
}

static char* duplicate_string(const std::string& str) {
    char* copy = new char[str.size() + 1];
    std::memcpy(copy, str.c_str(), str.size() + 1);
    return copy;
}

// Simple JSON parser for array of strings
static std::vector<std::string> parse_json_string_array(const std::string& json_str) {
    std::vector<std::string> lines;
    if (json_str.empty()) return lines;

    size_t i = 0;
    while (i < json_str.size()) {
        if (json_str[i] == '"') {
            i++;
            std::string current;
            bool escaped = false;
            while (i < json_str.size()) {
                char c = json_str[i];
                if (escaped) {
                    if (c == 'n') current += '\n';
                    else if (c == 't') current += '\t';
                    else if (c == 'r') current += '\r';
                    else if (c == '"') current += '"';
                    else if (c == '\\') current += '\\';
                    else current += c;
                    escaped = false;
                } else {
                    if (c == '\\') {
                        escaped = true;
                    } else if (c == '"') {
                        i++;
                        break;
                    } else {
                        current += c;
                    }
                }
                i++;
            }
            if (!current.empty()) {
                lines.push_back(current);
            }
        } else {
            i++;
        }
    }

    // Fallback: If not a JSON array, split by newline
    if (lines.empty() && !json_str.empty()) {
        std::stringstream ss(json_str);
        std::string item;
        while (std::getline(ss, item)) {
            if (!item.empty() && item != "[" && item != "]") {
                lines.push_back(item);
            }
        }
    }

    return lines;
}

// Simple JSON parser for metrics dictionary: {"cpu": 90, "latency_ms": [200, 1200]}
static std::map<std::string, std::vector<double>> parse_json_metrics(const std::string& json_str) {
    std::map<std::string, std::vector<double>> metrics_map;
    if (json_str.empty()) return metrics_map;

    size_t i = 0;
    while (i < json_str.size()) {
        if (json_str[i] == '"') {
            // Found a key
            i++;
            std::string key;
            while (i < json_str.size() && json_str[i] != '"') {
                key += json_str[i++];
            }
            if (i < json_str.size()) i++; // Skip closing quote

            // Skip until colon
            while (i < json_str.size() && json_str[i] != ':') i++;
            if (i < json_str.size()) i++; // Skip ':'

            // Skip whitespace
            while (i < json_str.size() && (json_str[i] == ' ' || json_str[i] == '\t' || json_str[i] == '\n')) i++;

            if (i < json_str.size()) {
                if (json_str[i] == '[') {
                    // Array of numbers
                    i++;
                    std::vector<double> vals;
                    std::string num_str;
                    while (i < json_str.size() && json_str[i] != ']') {
                        char c = json_str[i];
                        if ((c >= '0' && c <= '9') || c == '.' || c == '-' || c == '+') {
                            num_str += c;
                        } else if (c == ',' || c == ' ' || c == '\t' || c == '\n') {
                            if (!num_str.empty()) {
                                try { vals.push_back(std::stod(num_str)); } catch (...) {}
                                num_str.clear();
                            }
                        }
                        i++;
                    }
                    if (!num_str.empty()) {
                        try { vals.push_back(std::stod(num_str)); } catch (...) {}
                    }
                    if (i < json_str.size()) i++; // Skip ']'
                    metrics_map[key] = vals;
                } else {
                    // Single number or quoted number / string like "85%"
                    std::string num_str;
                    bool in_quotes = (json_str[i] == '"');
                    if (in_quotes) i++;

                    while (i < json_str.size()) {
                        char c = json_str[i];
                        if (in_quotes) {
                            if (c == '"') { i++; break; }
                            if ((c >= '0' && c <= '9') || c == '.' || c == '-' || c == '+') num_str += c;
                        } else {
                            if (c == ',' || c == '}' || c == ' ' || c == '\n') break;
                            if ((c >= '0' && c <= '9') || c == '.' || c == '-' || c == '+') num_str += c;
                        }
                        i++;
                    }
                    if (!num_str.empty()) {
                        try {
                            double val = std::stod(num_str);
                            metrics_map[key] = {val};
                        } catch (...) {}
                    }
                }
            }
        } else {
            i++;
        }
    }

    return metrics_map;
}

extern "C" {

AIOPS_API const char* aiops_get_version() {
    return "AI-Operations-Copilot C++ Core v2.0 (x86_64 C++17 Engine)";
}

AIOPS_API const char* aiops_analyze_logs(const char* logs_json) {
    if (!logs_json) return duplicate_string("{\"patterns\":[],\"total_logs\":0,\"error_count\":0}");

    auto lines = parse_json_string_array(logs_json);
    aiops::LogAnalyzer analyzer;
    auto result = analyzer.analyze(lines);

    std::ostringstream json;
    json << "{\n";
    json << "  \"total_logs\": " << result.total_logs << ",\n";
    json << "  \"error_count\": " << result.error_count << ",\n";
    json << "  \"warning_count\": " << result.warning_count << ",\n";
    json << "  \"patterns\": [\n";

    for (size_t i = 0; i < result.patterns.size(); ++i) {
        const auto& p = result.patterns[i];
        json << "    {\n";
        json << "      \"pattern\": \"" << escape_json(p.pattern_name) << "\",\n";
        json << "      \"frequency\": " << p.frequency << ",\n";
        json << "      \"severity\": \"" << escape_json(p.severity) << "\",\n";
        json << "      \"sample_lines\": [";
        for (size_t s = 0; s < p.sample_lines.size(); ++s) {
            json << "\"" << escape_json(p.sample_lines[s]) << "\"";
            if (s + 1 < p.sample_lines.size()) json << ", ";
        }
        json << "]\n";
        json << "    }" << (i + 1 < result.patterns.size() ? "," : "") << "\n";
    }

    json << "  ]\n";
    json << "}";

    return duplicate_string(json.str());
}

AIOPS_API const char* aiops_analyze_metrics(const char* metrics_json) {
    if (!metrics_json) return duplicate_string("{\"anomalies\":[],\"total_metrics_evaluated\":0}");

    auto metrics_data = parse_json_metrics(metrics_json);
    aiops::MetricsAnalyzer analyzer;
    auto result = analyzer.analyze(metrics_data);

    std::ostringstream json;
    json << "{\n";
    json << "  \"total_metrics_evaluated\": " << result.total_metrics_evaluated << ",\n";
    json << "  \"has_critical_anomaly\": " << (result.has_critical_anomaly ? "true" : "false") << ",\n";
    json << "  \"anomalies\": [\n";

    for (size_t i = 0; i < result.anomalies.size(); ++i) {
        const auto& a = result.anomalies[i];
        json << "    {\n";
        json << "      \"metric_name\": \"" << escape_json(a.metric_name) << "\",\n";
        json << "      \"value\": " << a.current_value << ",\n";
        json << "      \"peak_value\": " << a.peak_value << ",\n";
        json << "      \"threshold\": " << a.threshold << ",\n";
        json << "      \"z_score\": " << a.z_score << ",\n";
        json << "      \"severity\": \"" << escape_json(a.severity) << "\",\n";
        json << "      \"description\": \"" << escape_json(a.description) << "\"\n";
        json << "    }" << (i + 1 < result.anomalies.size() ? "," : "") << "\n";
    }

    json << "  ]\n";
    json << "}";

    return duplicate_string(json.str());
}

AIOPS_API const char* aiops_correlate(const char* logs_json, const char* metrics_json) {
    auto lines = logs_json ? parse_json_string_array(logs_json) : std::vector<std::string>{};
    auto metrics_data = metrics_json ? parse_json_metrics(metrics_json) : std::map<std::string, std::vector<double>>{};

    aiops::LogAnalyzer log_analyzer;
    auto log_result = log_analyzer.analyze(lines);

    aiops::MetricsAnalyzer metrics_analyzer;
    auto metrics_result = metrics_analyzer.analyze(metrics_data);

    aiops::Correlator correlator;
    auto root_cause = correlator.correlate(log_result, metrics_result);

    std::ostringstream json;
    json << "{\n";
    json << "  \"cause\": \"" << escape_json(root_cause.cause) << "\",\n";
    json << "  \"confidence_score\": " << std::fixed << std::setprecision(2) << root_cause.confidence_score << ",\n";
    json << "  \"primary_category\": \"" << escape_json(root_cause.primary_category) << "\",\n";
    json << "  \"reasoning\": \"" << escape_json(root_cause.reasoning) << "\",\n";
    json << "  \"contributing_factors\": [";
    for (size_t i = 0; i < root_cause.contributing_factors.size(); ++i) {
        json << "\"" << escape_json(root_cause.contributing_factors[i]) << "\"";
        if (i + 1 < root_cause.contributing_factors.size()) json << ", ";
    }
    json << "]\n";
    json << "}";

    return duplicate_string(json.str());
}

AIOPS_API void aiops_free_string(const char* ptr) {
    if (ptr) {
        delete[] ptr;
    }
}

} // extern "C"
