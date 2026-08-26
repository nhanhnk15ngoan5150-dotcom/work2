import pytest
from pydantic import ValidationError

from app.contracts.evidence import EvidenceDomain
from app.contracts.knowledge import (
    Chunk,
    Citation,
    Document,
    KnowledgeMetadata,
    RetrievalResult,
)


def _metadata(chunk_id: str | None = None) -> KnowledgeMetadata:
    return KnowledgeMetadata(
        tenant_id="dev_tenant",
        domains=[EvidenceDomain.KNOWLEDGE_OPERATION],
        knowledge_base_id="demo-operations",
        document_id="membership-rules",
        chunk_id=chunk_id,
        source="demo/membership.md",
        version="1.0",
    )


def test_document_and_chunk_keep_tenant_domain_and_source_metadata() -> None:
    document = Document(
        title="会员优惠规则",
        content="会员折扣不能与满减同时使用。",
        metadata=_metadata(),
    )
    chunk = Chunk(
        content=document.content,
        metadata=_metadata("membership-rules-001"),
    )

    assert document.metadata.tenant_id == "dev_tenant"
    assert chunk.metadata.domains == [EvidenceDomain.KNOWLEDGE_OPERATION]
    assert chunk.metadata.chunk_id == "membership-rules-001"


def test_chunk_requires_chunk_id() -> None:
    with pytest.raises(ValidationError, match="chunk_id"):
        Chunk(content="规则内容", metadata=_metadata())


def test_retrieval_result_contains_typed_citation() -> None:
    chunk = Chunk(
        content="会员折扣不能与满减同时使用。",
        metadata=_metadata("membership-rules-001"),
    )
    result = RetrievalResult(
        chunk=chunk,
        score=0.92,
        citation=Citation(
            document_id="membership-rules",
            chunk_id="membership-rules-001",
            source="demo/membership.md",
            version="1.0",
            excerpt=chunk.content,
        ),
    )

    assert result.score == 0.92
    assert result.citation.chunk_id == chunk.metadata.chunk_id


def test_retrieval_result_rejects_invalid_cosine_score() -> None:
    chunk = Chunk(content="规则内容", metadata=_metadata("chunk-001"))

    with pytest.raises(ValidationError):
        RetrievalResult(
            chunk=chunk,
            score=1.1,
            citation=Citation(
                document_id="membership-rules",
                chunk_id="chunk-001",
                source="demo/membership.md",
                version="1.0",
                excerpt="规则内容",
            ),
        )
