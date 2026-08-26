from collections.abc import Sequence
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Protocol, TypeVar

from app.contracts.weather import WeatherForecast, WeatherSnapshot
from app.contracts.evidence import EvidenceDomain
from app.contracts.knowledge import Chunk, Document, KnowledgeMetadata, RetrievalResult
from app.contracts.llm import LLMMessage, LLMResponse

SessionT_co = TypeVar("SessionT_co", covariant=True)


class DatabaseBackend(Protocol[SessionT_co]):
    """Own database session lifecycle without prescribing query representation."""

    def session(self) -> AbstractContextManager[SessionT_co]: ...


class LLMProvider(Protocol):
    """Vendor-neutral completion boundary."""

    async def complete(self, messages: Sequence[LLMMessage]) -> LLMResponse: ...


class EmbeddingProvider(Protocol):
    """Vendor-neutral embedding boundary."""

    async def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


class DocumentParser(Protocol):
    """Parser boundary for supported enterprise knowledge documents."""

    def parse(self, path: Path, metadata: KnowledgeMetadata) -> Document: ...


class WeatherProvider(Protocol):
    """Weather data source boundary."""

    async def current(self, location: str) -> WeatherSnapshot: ...

    async def forecast(self, location: str, days: int) -> list[WeatherForecast]: ...


class VectorStoreProvider(Protocol):
    """Vector persistence and similarity search boundary."""

    def upsert(
        self,
        chunks: Sequence[Chunk],
        vectors: Sequence[Sequence[float]],
    ) -> None: ...

    def search(
        self,
        vector: Sequence[float],
        *,
        tenant_id: str,
        domains: Sequence[EvidenceDomain],
        limit: int,
    ) -> list[RetrievalResult]: ...
