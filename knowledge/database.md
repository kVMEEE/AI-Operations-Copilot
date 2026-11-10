# Database contention
Version: 1

## Signals
Deadlock detected; connection pool exhausted; latency_ms; db_connections

## Diagnostics and uncertainty
Inspect blocking queries and pool occupancy. Use EXPLAIN without ANALYZE initially; ANALYZE executes queries and can affect workloads. Confirm timing before attributing latency.
Correlate event timing and deployment changes. Do not execute remediation automatically.

## Synthetic example — not a real incident
A fabricated training scenario contains Deadlock detected; connection pool exhausted; latency_ms; db_connections. The candidate category is Database contention; causality still requires corroborating evidence.
