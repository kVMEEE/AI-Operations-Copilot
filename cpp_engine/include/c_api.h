#ifndef AIOPS_C_API_H
#define AIOPS_C_API_H

#ifdef _WIN32
    #ifdef AIOPS_CORE_EXPORTS
        #define AIOPS_API __declspec(dllexport)
    #else
        #define AIOPS_API __declspec(dllimport)
    #endif
#else
    #define AIOPS_API __attribute__((visibility("default")))
#endif

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Get engine version and compiler metadata.
 */
AIOPS_API const char* aiops_get_version();

/**
 * Analyze a JSON array of log lines or a newline-separated string.
 * Returns a JSON string with structured patterns, error counts, and severity.
 * Caller MUST free the returned string using aiops_free_string().
 */
AIOPS_API const char* aiops_analyze_logs(const char* logs_json);

/**
 * Analyze a JSON object of metric time-series or single values.
 * Returns a JSON string with detected anomalies, Z-scores, and breach levels.
 * Caller MUST free the returned string using aiops_free_string().
 */
AIOPS_API const char* aiops_analyze_metrics(const char* metrics_json);

/**
 * Correlate log analysis JSON and metrics analysis JSON.
 * Returns a JSON string with probable cause, confidence score, and technical reasoning.
 * Caller MUST free the returned string using aiops_free_string().
 */
AIOPS_API const char* aiops_correlate(const char* logs_json, const char* metrics_json);

/**
 * Free string allocated by the C++ engine.
 */
AIOPS_API const char* aiops_analyze_incident(const char* logs_json, const char* metrics_json);

AIOPS_API void aiops_free_string(const char* ptr);

#ifdef __cplusplus
}
#endif

#endif // AIOPS_C_API_H
