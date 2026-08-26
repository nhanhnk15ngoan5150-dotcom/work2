from typing import cast

from app.contracts.evidence import Evidence, EvidenceDomain, EvidenceType
from app.contracts.knowledge import RetrievalResult
from app.contracts.state import AgentState
from app.domains.knowledge.exceptions import KnowledgeProviderError
from app.domains.knowledge.service import KnowledgeService

NO_KNOWLEDGE = "NO_KNOWLEDGE"


class KnowledgeOperationWorkflow:
    """Single-domain workflow for enterprise knowledge retrieval."""

    def __init__(self, knowledge_service: KnowledgeService) -> None:
        self._knowledge_service = knowledge_service

    @property
    def domain(self) -> EvidenceDomain:
        return EvidenceDomain.KNOWLEDGE_OPERATION

    # 1. 检索带 Tenant / Domain Guard 的企业知识
    async def execute(self, state: AgentState) -> AgentState:
        try:
            results = await self._knowledge_service.search(
                state["question"],
                tenant_id=state["tenant_id"],
            )
        except KnowledgeProviderError:
            return self._with_error(state, "知识检索服务暂时不可用")

        if not results:
            return self._with_no_knowledge(state)

        evidence = [self._to_evidence(state["tenant_id"], result) for result in results]
        result_state = dict(state)
        result_state["normalized_question"] = state["question"].replace(" ", "")
        result_state["evidence"] = evidence
        result_state["final_answer"] = self._format_answer(results[0])
        result_state["trace_metadata"] = {
            "knowledge_result_count": len(results),
            "knowledge_base_id": results[0].chunk.metadata.knowledge_base_id,
        }
        return cast(AgentState, result_state)

    # 2. 转换知识检索结果为带引用 Evidence
    @staticmethod
    def _to_evidence(tenant_id: str, result: RetrievalResult) -> Evidence:
        metadata = result.chunk.metadata
        return Evidence(
            tenant_id=tenant_id,
            domain=EvidenceDomain.KNOWLEDGE_OPERATION,
            evidence_type=EvidenceType.FACT,
            claim="企业知识库检索结果",
            value={
                "content": result.chunk.content,
                "score": result.score,
                "citation": result.citation.model_dump(mode="json"),
            },
            source_type="knowledge_base",
            source_id=(
                f"{metadata.knowledge_base_id}:"
                f"{metadata.document_id}:{metadata.chunk_id}:{metadata.version}"
            ),
            confidence=result.score if 0.0 <= result.score <= 1.0 else None,
        )

    # 3. 使用 Citation 生成确定性回答
    @staticmethod
    def _format_answer(result: RetrievalResult) -> str:
        citation = result.citation
        return (
            f"{result.chunk.content}"
            f"（来源：{citation.source}，版本：{citation.version}）"
        )

    @staticmethod
    def _with_no_knowledge(state: AgentState) -> AgentState:
        result = dict(state)
        result["evidence"] = []
        result["warnings"] = [NO_KNOWLEDGE]
        result["final_answer"] = "知识库中没有足够相关的信息"
        return cast(AgentState, result)

    @staticmethod
    def _with_error(state: AgentState, error: str) -> AgentState:
        result = dict(state)
        result["evidence"] = []
        result["errors"] = [error]
        result["final_answer"] = error
        return cast(AgentState, result)
