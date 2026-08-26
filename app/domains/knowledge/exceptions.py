class KnowledgeProviderError(RuntimeError):
    """External embedding or vector provider operation failed."""


class KnowledgeInvalidResponseError(KnowledgeProviderError):
    """An external knowledge provider returned an invalid response."""
