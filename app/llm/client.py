class LLMClient:
    """
    Wrapper around any LLM provider.
    """

    def analyze(self, prompt: str) -> str:
        # MOCK RESPONSE FOR NOW
        return f"[LLM ANALYSIS]: {prompt[:200]}"
