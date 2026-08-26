from __future__ import annotations

from collections.abc import Sequence
from math import isfinite
from typing import Any

import httpx

from app.domains.knowledge.exceptions import (
    KnowledgeInvalidResponseError,
    KnowledgeProviderError,
)


class OpenAICompatibleEmbeddingProvider:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 10.0,
        max_retries: int = 2,
    ) -> None:
        if not base_url.strip() or not api_key.strip() or not model.strip():
            raise ValueError("Embedding API configuration is incomplete")
        if timeout_seconds <= 0 or max_retries < 0:
            raise ValueError("Embedding retry configuration is invalid")
        self._endpoint = f"{base_url.rstrip('/')}/embeddings"
        self._api_key = api_key
        self._model = model
        self._client = client or httpx.AsyncClient()
        self._owns_client = client is None
        self._timeout = httpx.Timeout(timeout_seconds)
        self._max_retries = max_retries

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    # 1. 请求 OpenAI-compatible Embedding API
    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        payload = await self._request_json(
            {"model": self._model, "input": list(texts)}
        )
        data = payload.get("data")
        if not isinstance(data, list) or len(data) != len(texts):
            raise KnowledgeInvalidResponseError("Embedding data count is invalid")

        indexed_vectors: list[tuple[int, list[float]]] = []
        for item in data:
            if not isinstance(item, dict):
                raise KnowledgeInvalidResponseError("Embedding item is invalid")
            raw_vector = item.get("embedding")
            raw_index = item.get("index")
            if not isinstance(raw_vector, list) or not raw_vector:
                raise KnowledgeInvalidResponseError("Embedding vector is invalid")
            try:
                vector = [float(value) for value in raw_vector]
                index = int(raw_index)
            except (TypeError, ValueError) as exc:
                raise KnowledgeInvalidResponseError(
                    "Embedding item is invalid"
                ) from exc
            if any(not isfinite(value) for value in vector):
                raise KnowledgeInvalidResponseError("Embedding vector is not finite")
            indexed_vectors.append((index, vector))

        indexed_vectors.sort(key=lambda item: item[0])
        if [index for index, _ in indexed_vectors] != list(range(len(texts))):
            raise KnowledgeInvalidResponseError("Embedding indexes are invalid")
        dimensions = {len(vector) for _, vector in indexed_vectors}
        if len(dimensions) != 1:
            raise KnowledgeInvalidResponseError("Embedding dimensions do not match")
        return [vector for _, vector in indexed_vectors]

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
                raise KnowledgeProviderError("Embedding provider request failed") from exc
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code >= 500 and attempt < self._max_retries:
                    continue
                raise KnowledgeProviderError(
                    f"Embedding provider returned HTTP {exc.response.status_code}"
                ) from exc
            try:
                payload = response.json()
            except ValueError as exc:
                raise KnowledgeInvalidResponseError(
                    "Embedding provider returned invalid JSON"
                ) from exc
            if not isinstance(payload, dict):
                raise KnowledgeInvalidResponseError(
                    "Embedding response must be an object"
                )
            return payload
        raise KnowledgeProviderError("Embedding provider request failed")
