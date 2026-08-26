from collections.abc import Sequence

from app.contracts.providers import EmbeddingProvider


class EmbeddingService:
    def __init__(self, provider: EmbeddingProvider) -> None:
        self._provider = provider

    # 1. 生成标准化文本向量
    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        normalized = [text.strip() for text in texts]
        if not normalized or any(not text for text in normalized):
            raise ValueError("Embedding texts cannot be empty")
        vectors = await self._provider.embed(normalized)
        if len(vectors) != len(normalized):
            raise ValueError("Embedding result count does not match input")
        return vectors
