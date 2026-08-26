import asyncio

import httpx
import pytest

from app.contracts.llm import LLMMessage, LLMRole
from app.domains.llm.exceptions import LLMInvalidResponseError, LLMProviderError
from app.infrastructure.llm.openai_compatible import OpenAICompatibleLLMProvider

MESSAGES = [LLMMessage(role=LLMRole.USER, content="请综合证据")]


async def _complete(handler, *, max_retries: int = 2):
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = OpenAICompatibleLLMProvider(
            base_url="https://api.deepseek.com",
            api_key="test-key",
            model="deepseek-v4-flash",
            client=client,
            max_retries=max_retries,
        )
        return await provider.complete(MESSAGES)


def test_llm_provider_returns_content_usage_and_latency() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL(
            "https://api.deepseek.com/chat/completions"
        )
        assert request.headers["Authorization"] == "Bearer test-key"
        return httpx.Response(
            200,
            json={
                "model": "deepseek-v4-flash",
                "choices": [{"message": {"content": "综合建议"}}],
                "usage": {
                    "prompt_tokens": 20,
                    "completion_tokens": 10,
                    "total_tokens": 30,
                },
            },
        )

    result = asyncio.run(_complete(handler))

    assert result.content == "综合建议"
    assert result.model == "deepseek-v4-flash"
    assert result.input_tokens == 20
    assert result.output_tokens == 10
    assert result.total_tokens == 30
    assert result.latency_ms is not None
    assert result.estimated_cost is None


def test_llm_provider_keeps_missing_usage_as_none() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "回答"}}]},
        )

    result = asyncio.run(_complete(handler))

    assert result.input_tokens is None
    assert result.output_tokens is None
    assert result.total_tokens is None


def test_llm_provider_rejects_invalid_response() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    with pytest.raises(LLMInvalidResponseError):
        asyncio.run(_complete(handler))


def test_llm_provider_uses_finite_retry_for_network_and_5xx() -> None:
    attempts = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ConnectTimeout("timeout", request=request)
        return httpx.Response(503, request=request)

    with pytest.raises(LLMProviderError, match="HTTP 503"):
        asyncio.run(_complete(handler, max_retries=1))

    assert attempts == 2
