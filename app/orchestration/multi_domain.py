import logging
from typing import TypedDict, cast

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from app.contracts.domains import DomainWorkflow, RouteDecision
from app.contracts.evidence import EvidenceDomain
from app.contracts.orchestration import DomainExecutionResult
from app.contracts.multi_state import MultiDomainState
from app.contracts.state import AgentState
from app.orchestration.aggregator import EvidenceAggregator
from app.orchestration.evidence_validator import EvidenceValidator
from app.orchestration.planner import DeterministicPlanner

logger = logging.getLogger(__name__)


class DomainBranchState(TypedDict):
    request_id: str
    tenant_id: str
    session_id: str | None
    question: str
    domain: EvidenceDomain


class MultiDomainOrchestrator:
    """LangGraph map-reduce executor for selectively planned domains."""

    def __init__(
        self,
        planner: DeterministicPlanner,
        domain_workflows: dict[EvidenceDomain, DomainWorkflow],
        evidence_validator: EvidenceValidator | None = None,
        aggregator: EvidenceAggregator | None = None,
    ) -> None:
        if (evidence_validator is None) is not (aggregator is None):
            raise ValueError("Evidence validator and aggregator must be configured together")
        self._planner = planner
        self._domain_workflows = domain_workflows
        self._evidence_validator = evidence_validator
        self._aggregator = aggregator

        graph = StateGraph(MultiDomainState)
        graph.add_node("plan", self._plan)
        graph.add_node("execute_domain", self._execute_domain)
        graph.add_edge(START, "plan")
        graph.add_conditional_edges("plan", self._fan_out)
        if evidence_validator is None:
            graph.add_edge("execute_domain", END)
        else:
            graph.add_node("validate_evidence", self._validate_evidence)
            graph.add_node("aggregate", self._aggregate)
            graph.add_edge("execute_domain", "validate_evidence")
            graph.add_edge("validate_evidence", "aggregate")
            graph.add_edge("aggregate", END)
        self._graph = graph.compile()

    # 1. 执行 Planner 和动态 Fan-out / Fan-in
    async def execute(
        self,
        *,
        request_id: str,
        tenant_id: str,
        session_id: str | None,
        question: str,
        route_decision: RouteDecision,
    ) -> MultiDomainState:
        initial_state: MultiDomainState = {
            "request_id": request_id,
            "tenant_id": tenant_id,
            "session_id": session_id,
            "question": question,
            "route_decision": route_decision,
            "domain_results": [],
        }
        return cast(MultiDomainState, await self._graph.ainvoke(initial_state))

    def _plan(self, state: MultiDomainState) -> dict:
        return {"execution_plan": self._planner.plan(state["route_decision"])}

    # 2. 为每个计划 Domain 创建独立分支 State
    @staticmethod
    def _fan_out(state: MultiDomainState) -> list[Send]:
        plan = state["execution_plan"]
        return [
            Send(
                "execute_domain",
                DomainBranchState(
                    request_id=state["request_id"],
                    tenant_id=state["tenant_id"],
                    session_id=state["session_id"],
                    question=state["question"],
                    domain=domain,
                ),
            )
            for domain in plan.selected_domains
        ]

    # 3. 隔离执行 Domain 并提交结构化分支结果
    async def _execute_domain(self, branch: DomainBranchState) -> dict:
        domain = branch["domain"]
        workflow = self._domain_workflows.get(domain)
        if workflow is None:
            return {
                "domain_results": [
                    DomainExecutionResult(
                        domain=domain,
                        errors=[f"Domain workflow is not configured: {domain.value}"],
                        success=False,
                    )
                ]
            }

        state: AgentState = {
            "request_id": branch["request_id"],
            "tenant_id": branch["tenant_id"],
            "session_id": branch["session_id"],
            "question": branch["question"],
            "normalized_question": branch["question"],
            "selected_domains": [domain],
            "evidence": [],
            "errors": [],
            "warnings": [],
            "final_answer": None,
            "trace_metadata": {},
        }
        try:
            result = await workflow.execute(state)
        except Exception as exc:
            logger.exception("domain_execution_failed", extra={"domain": domain.value})
            domain_result = DomainExecutionResult(
                domain=domain,
                errors=[f"{type(exc).__name__}: domain execution failed"],
                success=False,
            )
        else:
            domain_result = DomainExecutionResult(
                domain=domain,
                evidence=list(result["evidence"]),
                warnings=list(result["warnings"]),
                errors=list(result["errors"]),
                trace_metadata=dict(result["trace_metadata"]),
                success=not result["errors"],
            )
        return {"domain_results": [domain_result]}

    # 4. Fan-in 后统一校验 Evidence
    def _validate_evidence(self, state: MultiDomainState) -> dict:
        if self._evidence_validator is None:
            raise RuntimeError("Evidence validator is not configured")
        result = self._evidence_validator.validate(
            tenant_id=state["tenant_id"],
            plan=state["execution_plan"],
            domain_results=state["domain_results"],
        )
        return {
            "validated_evidence": result.evidence,
            "validation_errors": result.errors,
        }

    # 5. 使用验证后的 Evidence 生成最终聚合结果
    async def _aggregate(self, state: MultiDomainState) -> dict:
        if self._aggregator is None:
            raise RuntimeError("Aggregator is not configured")
        domain_results = state["domain_results"]
        aggregation = await self._aggregator.aggregate(
            question=state["question"],
            plan=state["execution_plan"],
            evidence=state["validated_evidence"],
            domain_results=domain_results,
            validation_errors=state["validation_errors"],
        )
        trace_metadata = {
            "execution_mode": state["execution_plan"].execution_mode.value,
            "planned_domains": [
                domain.value for domain in state["execution_plan"].selected_domains
            ],
            "completed_domains": [
                result.domain.value for result in domain_results if result.success
            ],
            "failed_domains": [
                result.domain.value for result in domain_results if not result.success
            ],
            "evidence_count": len(state["validated_evidence"]),
            **aggregation.trace_metadata,
        }
        return {
            "aggregation_result": aggregation,
            "trace_metadata": trace_metadata,
        }
