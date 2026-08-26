from collections.abc import Sequence

from app.contracts.llm import LLMMessage, LLMResponse
from app.contracts.providers import LLMProvider


class LLMService:
    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    # 1. 请求结构化 LLM Provider
    async def complete(self, messages: Sequence[LLMMessage]) -> LLMResponse:
        if not messages:
            raise ValueError("LLM messages cannot be empty")
        return await self._provider.complete(messages)
