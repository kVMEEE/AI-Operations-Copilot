# Dependency/API decisions

Reviewed current official maintained source documentation on 2026-11-10. The normal docs.langchain.com and platform.openai.com documentation hosts returned proxy 403; their official GitHub source documentation was reachable:

- https://github.com/langchain-ai/langchain/blob/master/libs/partners/openai/langchain_openai/chat_models/base.py — ChatOpenAI `with_structured_output`, `method=json_schema`, strict schema, `include_raw`, timeout, max_tokens, max_retries.
- https://github.com/langchain-ai/langchain/blob/master/libs/partners/openai/langchain_openai/embeddings/base.py — OpenAIEmbeddings model, dimensions, request timeout, batching and retries.
- https://github.com/langchain-ai/langgraph/blob/main/libs/langgraph/langgraph/graph/state.py — StateGraph, explicit nodes, conditional edges and compilation.
- https://github.com/openai/openai-python/blob/main/README.md — structured response handling, retries, timeouts and typed SDK errors.

Installed and pinned: langchain-openai 1.7.4, langchain-core 1.7.7, langgraph 1.2.20. See constraints.txt for the full resolver result. Actual installed APIs are exercised in offline tests, including the real LangChain OpenAI adapter over a synthetic transport. Provider-side model availability and schema acceptance remain live-test prerequisites.

Markdown-it-py parses Markdown with raw HTML disabled; nh3 performs a second allowlist sanitization before HTML reaches the browser. No remote script/CDN is required by the dashboard. Pytest/pytest-asyncio/httpx and Playwright are development dependencies; PyQt6 is optional.

Python fallback uses the same log signatures and metric thresholds/statistics. Native output rounds some statistics during JSON serialization; comparisons should use tolerances. Fallback correlation deliberately exposes no fabricated heuristic score (zero compatibility value) and uses a simpler category decision chain; native correlation remains authoritative when available. Both engines are tested against the synthetic category fixtures. Unknown-category absence of telemetry is mapped to explicit abstention at the evidence layer.
