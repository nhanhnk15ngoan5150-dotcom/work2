import asyncio

import httpx
import pytest

from app.domains.knowledge.exceptions import KnowledgeInvalidResponseError
from app.infrastructure.knowledge.openai_embeddings import (
    OpenAICompatibleEmbeddingProvider,
)


async def _embed(handler, texts: list[str]) -> list[list[float]]:
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = OpenAICompatibleEmbeddingProvider(
            base_url="https://embedding.example/v1",
            api_key="test-key",
            model="test-model",
            client=client,
        )
        return await provider.embed(texts)


def test_openai_compatible_embedding_provider_orders_typed_vectors() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("https://embedding.example/v1/embeddings")
        assert request.headers["Authorization"] == "Bearer test-key"
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 1, "embedding": [0.0, 1.0]},
                    {"index": 0, "embedding": [1.0, 0.0]},
                ]
            },
        )

    vectors = asyncio.run(_embed(handler, ["会员规则", "雨天规范"]))

    assert vectors == [[1.0, 0.0], [0.0, 1.0]]


def test_openai_compatible_embedding_provider_rejects_invalid_response() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": []}]})

    with pytest.raises(KnowledgeInvalidResponseError):
        asyncio.run(_embed(handler, ["会员规则"]))
