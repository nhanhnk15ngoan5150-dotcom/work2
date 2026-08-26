from __future__ import annotations

from collections.abc import Sequence
from time import perf_counter
from typing import Any

import httpx
from pydantic import ValidationError

from app.contracts.llm import LLMMessage, LLMResponse
from app.domains.llm.exceptions import LLMInvalidResponseError, LLMProviderError


class OpenAICompatibleLLMProvider:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        if not base_url.strip() or not api_key.strip() or not model.strip():
            raise ValueError("LLM API configuration is incomplete")
        if timeout_seconds <= 0 or max_retries < 0:
            raise ValueError("LLM retry configuration is invalid")
        self._endpoint = f"{base_url.rstrip('/')}/chat/completions"
        self._api_key = api_key
        self._model = model
        self._client = client or httpx.AsyncClient()
        self._owns_client = client is None
        self._timeout = httpx.Timeout(timeout_seconds)
        self._max_retries = max_retries

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    # 1. 请求 OpenAI-compatible Chat Completions
    async def complete(self, messages: Sequence[LLMMessage]) -> LLMResponse:
        started_at = perf_counter()
        payload = await self._request_json(
            {
                "model": self._model,
                "messages": [message.model_dump(mode="json") for message in messages],
                "stream": False,
            }
        )
        latency_ms = (perf_counter() - started_at) * 1000
        try:
            choices = payload["choices"]
            first = choices[0]
            content = first["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("LLM content is empty")
            usage = payload.get("usage")
            usage_object = usage if isinstance(usage, dict) else {}
            return LLMResponse(
                content=content,
                model=(
                    str(payload["model"])
                    if payload.get("model") is not None
                    else None
                ),
                input_tokens=_optional_int(usage_object.get("prompt_tokens")),
                output_tokens=_optional_int(
                    usage_object.get("completion_tokens")
                ),
                total_tokens=_optional_int(usage_object.get("total_tokens")),
                latency_ms=latency_ms,
            )
        except (KeyError, IndexError, TypeError, ValueError, ValidationError) as exc:
            raise LLMInvalidResponseError("LLM response is invalid") from exc

    async def _request_json(self, body: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.post(
                    self._endpoint,
                    json=body,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    timeout=self._timeout,
                )
                response.raise_for_status()
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if attempt < self._max_retries:
                    continue
                raise LLMProviderError("LLM provider request failed") from exc
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code >= 500 and attempt < self._max_retries:
                    continue
                raise LLMProviderError(
                    f"LLM provider returned HTTP {exc.response.status_code}"
                ) from exc
            try:
                payload = response.json()
            except ValueError as exc:
                raise LLMInvalidResponseError(
                    "LLM provider returned invalid JSON"
                ) from exc
            if not isinstance(payload, dict):
                raise LLMInvalidResponseError("LLM response must be an object")
            return payload
        raise LLMProviderError("LLM provider request failed")


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)
