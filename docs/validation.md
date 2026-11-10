# Executed validation and delivery

Implementation commit: `d6fc275`, on `feature/evidence-investigation`, preserving `5c6cb50`. Branch push succeeded. `gh pr create --draft --base main --head feature/evidence-investigation` failed with `Post https://api.github.com/graphql: Forbidden`. No PR was created, merged or deployed. Prepared PR text is in [pull-request.md](pull-request.md).

Executed checks:

- `make -C cpp_engine`: native Linux library rebuilt successfully.
- `python tests/test_cpp_core.py`: all four native checks passed, before and after implementation.
- `python tests/test_e2e_workflow.py`: completed database workflow with report, before and after implementation.
- `.venv/bin/python -m pytest -q`: **41 passed** on final application code.
- New venv `/tmp/aiops-clean-venv`, installation from `requirements-dev.txt`, then pytest: **41 passed**.
- `python -m pip check`: no broken requirements.
- `python -m app.investigation.evaluate --output docs/evaluation-results.json`: 11/11 synthetic categories; lexical document recall@4 8/8.
- `python tests/evaluate_fake.py`: 11/11 fake-provider fixture labels, validated schemas and supplied references. This copies rule hypotheses and does not measure real LLM quality.
- `python -m app.investigation.evaluate --live`: explicitly **skipped: no credentials**.
- `python tests/browser_smoke.py --url http://127.0.0.1:8011`: real headless Chromium submission, deterministic fallback, evidence/citations, persisted history after reload, injection escaping and no JavaScript errors passed.
- `QT_QPA_PLATFORM=offscreen` PyQt6 MainWindow smoke: completed an investigation through the shared service, rendered the database report and actual modes.
- Final Docker image build succeeded with TLS verification and a mounted proxy CA. Container HTTP health and `/analyze/` passed with native analytics, persisted report, compatibility fields and sanitized HTML.
- `git diff --check` passed. Staged files were reviewed; credential-pattern hits were redaction patterns and synthetic test values, not credentials. No generated databases, environment secrets, binaries or venv were added.

Unverified: real OpenAI chat/embedding access and semantic retrieval quality (no API key), Windows build/runtime, public/multi-user operation (unsupported by design). The native/Docker/browser checks establish the tested local workflow only. They do not establish production security, scalability or accuracy.

## Grounding fixes — 2026-11-11

On `fix/investigation-grounding`, based on `feature/evidence-investigation`:

- Runbook regressions cover heading/body edits, whole-document version refresh, unchanged-vector reuse, lexical-only invalidation, model changes and deletion.
- Diagnostics now carry validated evidence IDs, applicable runbook citations, prerequisites and operational impact; deterministic mode covers database, memory, network, disk, CPU and insufficient/normal observations.
- Verification tests cover unsupported categories, Unknown uncertainty/missing information, contradictions, cross-incident references, unseen citations, one successful repair and failed revisions that discard proposals.
- Integration checks cover verified non-leading selections, bounded complete model messages/calls/duration, semantic failure/timeout lexical fallback (including tool search), and provider initialization/runtime failures preserving deterministic reports.
- `make -C cpp_engine`: build check passed; existing native outputs were up to date. Both documented native and E2E scripts passed.
- `.venv/bin/python -m pytest -q`: **64 passed**, including HTTP lifecycle and verified-selection response tests.
- Real Chromium smoke on the local server passed, including category-specific diagnostics, prerequisites, operational impact, history and injection escaping. No UI redesign was made.
- Synthetic evaluation retained 11/11 authored category agreement and 8/8 lexical document recall@4. These remain regression metrics, not production accuracy estimates.
- `pip check` and `git diff --check` passed. No chat/embedding credential was configured; the opt-in live evaluator reported `skipped: no credentials`. Live OpenAI and embeddings remain unverified.
