The application previously repeated native analytics, lost jobs on restart, and had no real model/retrieval investigation path. This adds a shared evidence-grounded service with single-pass C++ analytics, versioned SQLite retrieval, a bounded LangGraph tool loop through the real LangChain OpenAI adapter, deterministic verification/fallback, and persisted jobs/results/stages.

The dashboard now exposes evidence, hypotheses, provenance, traces and actual execution modes with sanitized Markdown. The desktop uses the shared service. Dependencies, setup, Docker, synthetic fixtures and requirement-by-requirement limitations are documented.

Validation: 41 offline tests pass, including a clean venv run; native and E2E scripts pass; Chromium submission/history/injection smoke passes; PyQt offscreen smoke passes; final Docker build and HTTP/native-analysis smoke pass. Synthetic evaluation: 11/11 authored category labels and 8/8 lexical document recall@4. These are regression fixtures, not production accuracy claims.

Live OpenAI/embedding calls were skipped because no credentials were available. Real LangChain request/response handling was exercised over a synthetic HTTP transport. Windows execution and real semantic-retrieval quality remain unverified. This remains an unauthenticated local/private, single-process application; no deployment or merge is requested.
