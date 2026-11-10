# Network timeouts
Version: 1

## Signals
Connection timed out; ETIMEDOUT; network_drop_rate; latency_ms

## Diagnostics and uncertainty
Inspect dependency health and DNS evidence. Distinguish connection refusal from timeout. Active probes generate traffic; review scope first.
Correlate event timing and deployment changes. Do not execute remediation automatically.

## Synthetic example — not a real incident
A fabricated training scenario contains Connection timed out; ETIMEDOUT; network_drop_rate; latency_ms. The candidate category is Network timeouts; causality still requires corroborating evidence.
