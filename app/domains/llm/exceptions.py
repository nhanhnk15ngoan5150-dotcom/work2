class LLMProviderError(RuntimeError):
    """Expected LLM provider failure."""


class LLMInvalidResponseError(LLMProviderError):
    """The LLM provider returned an invalid response."""
