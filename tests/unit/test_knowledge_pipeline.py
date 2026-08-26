import asyncio
from pathlib import Path

from app.contracts.evidence import EvidenceDomain
from app.contracts.knowledge import Chunk, Document, KnowledgeMetadata
from app.domains.knowledge.chunker import KnowledgeChunker
from app.domains.knowledge.embedding_service import EmbeddingService
from app.domains.knowledge.indexer import KnowledgeIndexer
from app.domains.knowledge.parser import TextDocumentParser
from app.domains.knowledge.retriever import KnowledgeRetriever
from app.infrastructure.knowledge.local_vector_store import LocalVectorStore

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class FakeEmbeddingProvider:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    @staticmethod
    def _vector(text: str) -> list[float]:
        if any(keyword in text for keyword in ("会员", "折扣", "满减")):
            return [1.0, 0.0]
        if any(keyword in text for keyword in ("雨天", "降雨", "防滑")):
            return [0.0, 1.0]
        return [-1.0, 0.0]


def _metadata(
    *,
    tenant_id: str = "dev_tenant",
    domain: EvidenceDomain = EvidenceDomain.KNOWLEDGE_OPERATION,
    document_id: str = "membership-rules",
    chunk_id: str | None = None,
) -> KnowledgeMetadata:
    return KnowledgeMetadata(
        tenant_id=tenant_id,
        domains=[domain],
        knowledge_base_id="demo-operations",
        document_id=document_id,
        chunk_id=chunk_id,
        source=f"data/demo_knowledge/{document_id}.md",
        version="1.0",
    )


def test_text_parser_and_chunker_create_deterministic_metadata() -> None:
    path = PROJECT_ROOT / "data" / "demo_knowledge" / "membership_rules.md"
    document = TextDocumentParser().parse(path, _metadata())
    chunks = KnowledgeChunker(max_chars=50, overlap_chars=10).split(document)

    assert document.title == "会员优惠规则（演示）"
    assert len(chunks) >= 2
    assert chunks[0].metadata.chunk_id == "membership-rules:0001"
    assert chunks[1].metadata.chunk_id == "membership-rules:0002"
    assert all(chunk.metadata.tenant_id == "dev_tenant" for chunk in chunks)


def test_local_vector_store_enforces_tenant_and_domain_guards() -> None:
    store = LocalVectorStore()
    chunks = [
        Chunk(content="本租户会员规则", metadata=_metadata(chunk_id="allowed")),
        Chunk(
            content="其他租户会员规则",
            metadata=_metadata(tenant_id="other_tenant", chunk_id="other"),
        ),
        Chunk(
            content="经营数据定义",
            metadata=_metadata(
                domain=EvidenceDomain.BUSINESS_DATA,
                chunk_id="business",
            ),
        ),
    ]
    store.upsert(chunks, [[1.0, 0.0], [1.0, 0.0], [1.0, 0.0]])

    results = store.search(
        [1.0, 0.0],
        tenant_id="dev_tenant",
        domains=[EvidenceDomain.KNOWLEDGE_OPERATION],
        limit=5,
    )

    assert [result.chunk.metadata.chunk_id for result in results] == ["allowed"]


def test_index_retrieve_threshold_returns_knowledge_or_no_knowledge() -> None:
    embedding_service = EmbeddingService(FakeEmbeddingProvider())
    store = LocalVectorStore()
    document = Document(
        title="会员优惠规则",
        content="会员折扣与满减优惠不能同时使用。",
        metadata=_metadata(),
    )
    indexer = KnowledgeIndexer(
        KnowledgeChunker(max_chars=100, overlap_chars=10),
        embedding_service,
        store,
    )
    indexed_count = asyncio.run(indexer.index([document]))
    retriever = KnowledgeRetriever(
        embedding_service,
        store,
        threshold=0.8,
        top_k=3,
    )

    matched = asyncio.run(
        retriever.retrieve(
            "会员折扣和满减能否同时使用？",
            tenant_id="dev_tenant",
            domains=[EvidenceDomain.KNOWLEDGE_OPERATION],
        )
    )
    missing = asyncio.run(
        retriever.retrieve(
            "公司春节奖金规则是什么？",
            tenant_id="dev_tenant",
            domains=[EvidenceDomain.KNOWLEDGE_OPERATION],
        )
    )

    assert indexed_count == 1
    assert matched[0].score == 1.0
    assert matched[0].citation.document_id == "membership-rules"
    assert missing == []
