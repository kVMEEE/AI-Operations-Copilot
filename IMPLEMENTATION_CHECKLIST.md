# Evidence-grounded investigation upgrade

Baseline: original C++/Python application; feature branch created. Existing tests run before changes.

- [x] Inspect existing schemas, workflow, native bridge, API and build configuration
- [ ] Complete first-party code audit and official API documentation review
- [ ] Single-pass analytics and validated evidence contracts
- [ ] Real bounded LangChain provider integration
- [ ] Persistent hybrid retrieval and knowledge fixtures
- [ ] Bounded LangGraph tool investigation and verification
- [ ] Persistent job lifecycle and shared service
- [ ] Safe dashboard and desktop compatibility
- [ ] Offline tests, evaluation and browser smoke
- [ ] Reproducible installation and documentation
- [ ] Final diff review, commit and draft PR

No live provider calls authorized for real incident data. Synthetic live checks only, when credentials are available. No deployment or public exposure.

## Validation of initial changes

Both documented integration scripts passed before and after these changes.
Manual validation rejected booleans, strings, objects, empty series, NaN and mixed metric series, and accepted finite numeric series. `git diff --check` passed.

Initial changes bound incident descriptions, log payloads and metric series; reject nonnumeric/nonfinite metrics; label heuristic scores as uncalibrated; distinguish analysis completion from resolution; remove the report's universal safety assertion.

The architecture upgrade is NOT complete. No provider, retrieval, LangGraph, persistence, browser, desktop, Docker or live-model validation has been completed in this implementation pass.
