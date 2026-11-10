# Evidence-grounded investigation upgrade

Continued on `feature/evidence-investigation`, preserving initial commit `5c6cb50`.

- [x] Inspect first-party application/native/UI code and run baseline checks
- [x] Review official maintained integration source documentation
- [x] Single-pass native analytics, explicit Python fallback and typed evidence
- [x] Real configurable LangChain OpenAI integration with structured responses and budgets
- [x] Persistent heading-aware lexical/vector index and provenance-preserving hybrid retrieval
- [x] Bounded LangGraph tool loop, ownership validation, verification and one revision
- [x] Shared service, SQLite jobs/stages/results, cancellation and restart recovery
- [x] Dashboard evidence/hypotheses/citations/traces/modes and sanitized Markdown
- [x] Desktop shared-service integration and offscreen smoke
- [x] Offline tests, synthetic/fake-provider evaluation and real Chromium smoke
- [x] Pinned dependencies, fresh install, Docker build and HTTP smoke
- [x] Architecture, setup, security, limits and requirement reconciliation documentation
- [ ] Live provider/embedding service verification — blocked: no API credentials
- [ ] Windows execution — unavailable in this Linux environment
- [x] Final implementation committed as d6fc275 and pushed to origin/feature/evidence-investigation
- [ ] Draft PR creation — blocked: GitHub GraphQL returned Forbidden; attempted with gh pr create --draft. Reviewable text is in docs/pull-request.md.

See docs/requirements.md for all thirteen original specification areas, implemented behavior and limits. No public deployment or merge is authorized or performed.
