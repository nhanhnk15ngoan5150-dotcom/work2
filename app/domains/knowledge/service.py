from app.contracts.evidence import EvidenceDomain
from app.contracts.knowledge import RetrievalResult
from app.domains.knowledge.retriever import KnowledgeRetriever


class KnowledgeService:
    def __init__(self, retriever: KnowledgeRetriever) -> None:
        self._retriever = retriever

    # 1. 检索企业经营知识
    async def search(
        self,
        question: str,
        *,
        tenant_id: str,
    ) -> list[RetrievalResult]:
        return await self._retriever.retrieve(
            question,
            tenant_id=tenant_id,
            domains=[EvidenceDomain.KNOWLEDGE_OPERATION],
        )
