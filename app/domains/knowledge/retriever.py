from collections.abc import Sequence

from app.contracts.evidence import EvidenceDomain
from app.contracts.knowledge import RetrievalResult
from app.contracts.providers import VectorStoreProvider
from app.domains.knowledge.embedding_service import EmbeddingService


class KnowledgeRetriever:
    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: VectorStoreProvider,
        *,
        threshold: float = 0.75,
        top_k: int = 3,
    ) -> None:
        if not -1.0 <= threshold <= 1.0:
            raise ValueError("Retrieval threshold must be between -1 and 1")
        if top_k <= 0:
            raise ValueError("Retrieval top_k must be positive")
        self._embedding_service = embedding_service
        self._vector_store = vector_store
        self._threshold = threshold
        self._top_k = top_k

    # 1. 执行 Tenant / Domain Guard 后的向量检索
    async def retrieve(
        self,
        question: str,
        *,
        tenant_id: str,
        domains: Sequence[EvidenceDomain],
    ) -> list[RetrievalResult]:
        normalized = question.strip()
        if not normalized:
            return []
        if not tenant_id:
            raise ValueError("Retrieval tenant_id is required")
        if not domains:
            raise ValueError("Retrieval domains are required")

        vector = (await self._embedding_service.embed([normalized]))[0]
        results = self._vector_store.search(
            vector,
            tenant_id=tenant_id,
            domains=domains,
            limit=self._top_k,
        )
        return [result for result in results if result.score >= self._threshold]
