# Original requirement reconciliation

This records implementation and verification, not a production-readiness claim.

| Original area | Implemented and exercised | Limits / external verification |
| --- | --- | --- |
| 1. Starting point | Preserved commit 5c6cb50 and branch; inspected first-party Python, C++, UI, tests/build files; baseline scripts passed; persistent checklist; official maintained integration source docs reviewed | Documentation web hosts returned proxy 403; official GitHub sources used instead |
| 2. Shared architecture | Validated/redacted input → native evidence → hypotheses → retrieval → LangGraph tool investigation → verification/one revision → sanitized report → SQLAlchemy persistence; HTTP and desktop share PlannerAgent | Single trusted local operator; one application process |
| 3. Deterministic analytics | New single-pass C ABI analyzes each domain once and reuses results for correlation; async thread offload; no artificial progress sleeps; fallback tested; engine recorded; unsupported disk/CPU/network causal prose corrected | Old C ABI calls retained for compatibility; fallback correlation/rounding differences documented; native heuristics are not calibrated probabilities |
| 4. Typed contracts | Pydantic evidence, findings, hypotheses, chunks, citations, numeric claims, diagnostics, verification, trace, provider metadata, final report; typed graph state; finite/bounded input | Evidence timestamps remain null unless established; no timestamp extraction model; log evidence represents classified patterns plus source sample line indices |
| 5. Real provider | Maintained LangChain OpenAI structured adapter; configured models; timeout/token/call bounds; one retry/repair; usage metadata; disabled mode; real adapter tested with synthetic HTTP and rate-limit response | No API keys present. Live OpenAI calls and actual model schema acceptance unverified. Fake provider exists only in tests |
| 6. RAG | Heading-aware Markdown chunks; stable IDs, source/heading/hash/version; incremental SQLite vectors; model/dimension compatibility; stale-source indication; cosine and lexical rankings; reciprocal rank fusion; LangChain BaseRetriever; explicit indexing CLI | Real embeddings/semantic quality unverified without credentials. Semantic/vector storage and fusion tested with labelled fake vectors; lexical document recall@4 evaluated separately |
| 7. LangGraph | Explicit collect/retrieve/investigate/tool/verify/revise/finalize nodes; conditional bounded tool loop; five read-only tools; validated ownership; duplicate detection; total steps/calls/duration/context/output limits; concise trace | Tool requests use schema-constrained decision envelopes executed by graph, rather than an unrestricted agent executor; no arbitrary tools or private reasoning stored |
| 8. Verification/security | IDs and incident ownership; supplied citation snapshots; numeric claim equality; category support/contradiction membership; action labels; extra claim fields forbidden; one revision then deterministic fallback; redaction and HTML sanitization tested | Restricts expressive free-form LLM claims intentionally. No semantic-faithfulness proof. Common-format redaction is incomplete by nature; prompt injection risk reduced, not eliminated |
| 9. Persistence/execution | SQLAlchemy schema v1; job input/status and full validated result envelope; stage history; bounded queue/semaphore; retained tasks; scoped sessions; cancellation, shutdown, restart recovery tested | Evidence/citations/traces stored in the result JSON envelope rather than separate normalized tables. No distributed durability, automatic retries, retention UI or multi-worker support |
| 10. API/dashboard/desktop | Both analysis APIs share service; compatibility fields retained; evidence/citation/trace/stage endpoints; deterministic/LLM selection; escaped strings; sanitized Markdown; persisted history; actual modes/fallback; desktop shared service | Read endpoints are scoped by incident ID but unauthenticated; not tenant isolation. Desktop deterministic mode only; Windows interactive UI not exercised |
| 11. Tests/evaluation | Existing native/E2E scripts; offline tests for validation, native/fallback, all tools, budgets, retries/repair, rate limits, citation/ownership/numeric checks, redaction, index updates/mismatch/staleness, queue/cancel/restart, HTTP; synthetic 11-case evaluation; fake-provider evaluation; browser injection/history smoke; offscreen desktop | Live tests explicitly skipped for missing keys. Synthetic metrics do not imply production accuracy. Browser smoke is not a full accessibility or cross-browser audit |
| 12. Setup/deployment/docs | Pinned direct/transitive dependencies; fresh venv install; native build; DB/index CLI; .env.example; Docker non-root one-worker image; build and HTTP smoke; Windows script anchors its directory; architecture/security/limits documented | Windows execution not tested. Docker and local Linux checks are distinct from deployment; no deployment performed |
| 13. Delivery | Final tests/diff/secret inspection, feature-branch commits and PR attempt recorded in delivery report | GitHub GraphQL API returned Forbidden in this environment; branch push and draft-PR results reported separately |

## Evaluation interpretation

The deterministic fixture evaluation achieved 11/11 category agreement and 8/8 lexical document recall@4 queries. The insufficient-evidence case abstains as Unknown, misleading descriptions do not override telemetry, and conflicts retain contradictory metrics. A healthy category means only that configured rules found no anomalies, not proof of system health.

The fake-provider evaluation is explicitly synthetic and mostly copies deterministic hypotheses. Its schema/reference success is a plumbing check, not an LLM capability claim. Citation validity is reference integrity, not semantic support. Actual provider token usage is unavailable without live calls; fake metadata is never presented as billed usage.

## Interview explanation

The native C++ core measures telemetry once. Python turns those measurements into incident-scoped evidence and baseline hypotheses. A LangChain retriever supplies versioned operational context. A LangGraph state machine lets a configured model request only bounded evidence/runbook tools, then validates a constrained structured proposal. Unsupported proposals get one revision and then deterministic fallback. SQLite keeps jobs, evidence and traces across restarts, and the UI exposes uncertainty and actual execution modes.

## Capability statements suitable for a resume

- Evidence-grounded incident investigation application combining C++17 analytics, FastAPI, LangChain and bounded LangGraph orchestration.
- Persistent hybrid retrieval with versioned Markdown provenance, SQLite embeddings and explicit lexical fallback.
- Typed verification of citations, incident ownership and numerical claims, plus cancellation/recovery and offline adversarial tests.

These describe repository capabilities, not a claim about any individual's contribution, production deployment or business impact.
