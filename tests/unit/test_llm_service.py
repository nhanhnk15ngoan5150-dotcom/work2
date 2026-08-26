import asyncio
from unittest.mock import AsyncMock

from app.contracts.llm import LLMMessage, LLMResponse, LLMRole
from app.contracts.providers import LLMProvider
from app.domains.llm.service import LLMService


def test_llm_service_delegates_typed_messages_and_response() -> None:
    provider = AsyncMock(spec=LLMProvider)
    response = LLMResponse(content="综合建议", model="deepseek-v4-flash")
    provider.complete.return_value = response
    messages = [LLMMessage(role=LLMRole.USER, content="请综合证据")]

    result = asyncio.run(LLMService(provider).complete(messages))

    assert result is response
    provider.complete.assert_awaited_once_with(messages)
