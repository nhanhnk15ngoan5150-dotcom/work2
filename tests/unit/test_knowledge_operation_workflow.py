import asyncio
from unittest.mock import AsyncMock

from app.contracts.evidence import EvidenceDomain, EvidenceType
from app.contracts.knowledge import (
    Chunk,
    Citation,
    KnowledgeMetadata,
    RetrievalResult,
)
from app.contracts.state import AgentState
from app.domains.knowledge.exceptions import KnowledgeProviderError
from app.domains.knowledge.service import KnowledgeService
from app.workflows.knowledge_operation import (
    NO_KNOWLEDGE,
    KnowledgeOperationWorkflow,
)


def _state(question: str) -> AgentState:
    return {
        "request_id": "knowledge-test",
        "tenant_id": "dev_tenant",
        "session_id": None,
        "question": question,
        "normalized_question": question,
        "selected_domains": [EvidenceDomain.KNOWLEDGE_OPERATION],
        "evidence": [],
        "errors": [],
        "warnings": [],
        "final_answer": None,
        "trace_metadata": {},
    }


def _retrieval_result() -> RetrievalResult:
    metadata = KnowledgeMetadata(
        tenant_id="dev_tenant",
        domains=[EvidenceDomain.KNOWLEDGE_OPERATION],
        knowledge_base_id="demo-operations",
        document_id="membership-rules",
        chunk_id="membership-rules:0001",
        source="data/demo_knowledge/membership_rules.md",
        version="1.0",
    )
    chunk = Chunk(
        content="会员折扣与满减优惠不能同时使用。",
        metadata=metadata,
    )
    return RetrievalResult(
        chunk=chunk,
        score=0.92,
        citation=Citation(
            document_id=metadata.document_id,
            chunk_id=metadata.chunk_id or "",
            source=metadata.source,
            version=metadata.version,
            excerpt=chunk.content,
        ),
    )


def test_knowledge_workflow_returns_cited_evidence() -> None:
    service = AsyncMock(spec=KnowledgeService)
    service.search.return_value = [_retrieval_result()]

    result = asyncio.run(
        KnowledgeOperationWorkflow(service).execute(
            _state("会员折扣和满减可以同时使用吗？")
        )
    )

    evidence = result["evidence"][0]
    assert evidence.domain is EvidenceDomain.KNOWLEDGE_OPERATION
    assert evidence.evidence_type is EvidenceType.FACT
    assert evidence.value["score"] == 0.92
    assert evidence.confidence is None
    assert evidence.value["citation"]["chunk_id"] == "membership-rules:0001"
    assert "来源：data/demo_knowledge/membership_rules.md" in result["final_answer"]
    service.search.assert_awaited_once_with(
        "会员折扣和满减可以同时使用吗？",
        tenant_id="dev_tenant",
    )


def test_knowledge_workflow_returns_no_knowledge_without_evidence() -> None:
    service = AsyncMock(spec=KnowledgeService)
    service.search.return_value = []

    result = asyncio.run(
        KnowledgeOperationWorkflow(service).execute(
            _state("公司春节奖金规则是什么？")
        )
    )

    assert result["evidence"] == []
    assert result["warnings"] == [NO_KNOWLEDGE]
    assert result["final_answer"] == "知识库中没有足够相关的信息"


def test_knowledge_workflow_handles_provider_error() -> None:
    service = AsyncMock(spec=KnowledgeService)
    service.search.side_effect = KnowledgeProviderError("unavailable")

    result = asyncio.run(
        KnowledgeOperationWorkflow(service).execute(_state("会员规则是什么？"))
    )

    assert result["evidence"] == []
    assert result["errors"] == ["知识检索服务暂时不可用"]
