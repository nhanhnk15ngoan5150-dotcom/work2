from collections.abc import Mapping, Sequence
from contextlib import AbstractContextManager
from typing import Any, Protocol, TypeVar

SessionT_co = TypeVar("SessionT_co", covariant=True)


class DatabaseBackend(Protocol[SessionT_co]):
    """Own database session lifecycle without prescribing query representation."""

    def session(self) -> AbstractContextManager[SessionT_co]: ...


class LLMProvider(Protocol):
    """Vendor-neutral completion boundary."""

    async def complete(self, messages: Sequence[Mapping[str, str]]) -> str: ...


class EmbeddingProvider(Protocol):
    """Vendor-neutral embedding boundary."""

    async def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


class WeatherProvider(Protocol):
    """Weather data source boundary."""

    async def current(self, location: str) -> Mapping[str, Any]: ...

    async def forecast(self, location: str, days: int) -> Sequence[Mapping[str, Any]]: ...


class VectorStoreProvider(Protocol):
    """Vector persistence and similarity search boundary."""

    def upsert(self, items: Sequence[Mapping[str, Any]]) -> None: ...

    def search(
        self,
        vector: Sequence[float],
        *,
        tenant_id: str,
        limit: int,
    ) -> Sequence[Mapping[str, Any]]: ...
