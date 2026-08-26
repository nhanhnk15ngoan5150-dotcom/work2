import asyncio
from time import perf_counter

from app.contracts.domains import RouteDecision
from app.contracts.evidence import Evidence, EvidenceDomain, EvidenceType
from app.contracts.state import AgentState
from app.orchestration.multi_domain import MultiDomainOrchestrator
from app.orchestration.planner import DeterministicPlanner


class DelayedWorkflow:
    def __init__(
        self,
        domain: EvidenceDomain,
        state_ids: list[int],
        delay: float = 0.2,
    ) -> None:
        self._domain = domain
        self._state_ids = state_ids
        self._delay = delay

    @property
    def domain(self) -> EvidenceDomain:
        return self._domain

    async def execute(self, state: AgentState) -> AgentState:
        self._state_ids.append(id(state))
        assert state["selected_domains"] == [self._domain]
        await asyncio.sleep(self._delay)
        state["evidence"] = [
            Evidence(
                tenant_id=state["tenant_id"],
                domain=self._domain,
                evidence_type=EvidenceType.FACT,
                claim=f"{self._domain.value} completed",
                value={"domain": self._domain.value},
                source_type="test",
                source_id=f"test:{self._domain.value}",
            )
        ]
        state["trace_metadata"] = {"completed": self._domain.value}
        return state


def test_langgraph_dynamic_fan_out_runs_domains_in_parallel() -> None:
    state_ids: list[int] = []
    domains = [
        EvidenceDomain.BUSINESS_DATA,
        EvidenceDomain.EXTERNAL_FACTOR,
        EvidenceDomain.KNOWLEDGE_OPERATION,
    ]
    orchestrator = MultiDomainOrchestrator(
        DeterministicPlanner(),
        {
            domain: DelayedWorkflow(domain, state_ids)
            for domain in domains
        },
    )

    started_at = perf_counter()
    result = asyncio.run(
        orchestrator.execute(
            request_id="parallel-test",
            tenant_id="dev_tenant",
            session_id=None,
            question="multi-domain test",
            route_decision=RouteDecision(selected_domains=domains),
        )
    )
    elapsed = perf_counter() - started_at

    assert elapsed < 0.45
    assert len(set(state_ids)) == 3
    assert {item.domain for item in result["domain_results"]} == set(domains)
    assert sum(len(item.evidence) for item in result["domain_results"]) == 3


def test_domain_exception_isolated_as_failed_branch_result() -> None:
    class FailingWorkflow(DelayedWorkflow):
        async def execute(self, state: AgentState) -> AgentState:
            raise RuntimeError("sensitive provider details")

    domain = EvidenceDomain.EXTERNAL_FACTOR
    orchestrator = MultiDomainOrchestrator(
        DeterministicPlanner(),
        {domain: FailingWorkflow(domain, [], delay=0)},
    )

    result = asyncio.run(
        orchestrator.execute(
            request_id="failure-test",
            tenant_id="dev_tenant",
            session_id=None,
            question="weather and business",
            route_decision=RouteDecision(
                selected_domains=[domain, EvidenceDomain.BUSINESS_DATA]
            ),
        )
    )

    results = {item.domain: item for item in result["domain_results"]}
    assert results[domain].success is False
    assert results[domain].evidence == []
    assert results[domain].errors == ["RuntimeError: domain execution failed"]
    assert results[EvidenceDomain.BUSINESS_DATA].success is False
