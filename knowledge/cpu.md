# CPU and thread saturation
Version: 1

## Signals
Thread pool exhausted; RejectedExecutionException; cpu_usage; cpu_percent

## Diagnostics and uncertainty
Inspect CPU trends, queue depths and thread rejection logs. CPU pressure alone does not prove queue backlog. Profiling may add overhead.
Correlate event timing and deployment changes. Do not execute remediation automatically.

## Synthetic example — not a real incident
A fabricated training scenario contains Thread pool exhausted; RejectedExecutionException; cpu_usage; cpu_percent. The candidate category is CPU and thread saturation; causality still requires corroborating evidence.
