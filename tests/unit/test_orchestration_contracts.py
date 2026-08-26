import pytest
from pydantic import ValidationError

from app.contracts.evidence import Evidence, EvidenceDomain, EvidenceType
from app.contracts.orchestration import (
    AgentRoute,
    AggregationResult,
    DomainExecutionResult,
    ExecutionMode,
    ExecutionPlan,
)


def _evidence(domain: EvidenceDomain) -> Evidence:
    return Evidence(
        tenant_id="dev_tenant",
        domain=domain,
        evidence_type=EvidenceType.FACT,
        claim="Contract test evidence",
        value={"amount": 100},
        source_type="test",
        source_id=f"test:{domain.value}",
    )


def test_execution_plan_supports_single_and_multi_domain_modes() -> None:
    single = ExecutionPlan(
        selected_domains=[EvidenceDomain.BUSINESS_DATA],
        execution_mode=ExecutionMode.SINGLE_DOMAIN,
    )
    multi = ExecutionPlan(
        selected_domains=[
            EvidenceDomain.BUSINESS_DATA,
            EvidenceDomain.EXTERNAL_FACTOR,
            EvidenceDomain.KNOWLEDGE_OPERATION,
        ],
        execution_mode=ExecutionMode.MULTI_DOMAIN,
    )

    assert single.execution_mode is ExecutionMode.SINGLE_DOMAIN
    assert multi.selected_domains[2] is EvidenceDomain.KNOWLEDGE_OPERATION
    assert AgentRoute.from_domain(EvidenceDomain.BUSINESS_DATA).value == (
        "BUSINESS_DATA"
    )


@pytest.mark.parametrize(
    ("domains", "mode"),
    [
        (
            [EvidenceDomain.BUSINESS_DATA, EvidenceDomain.EXTERNAL_FACTOR],
            ExecutionMode.SINGLE_DOMAIN,
        ),
        ([EvidenceDomain.BUSINESS_DATA], ExecutionMode.MULTI_DOMAIN),
        (
            [EvidenceDomain.BUSINESS_DATA, EvidenceDomain.BUSINESS_DATA],
            ExecutionMode.MULTI_DOMAIN,
        ),
    ],
)
def test_execution_plan_rejects_invalid_domain_shape(domains, mode) -> None:
    with pytest.raises(ValidationError):
        ExecutionPlan(selected_domains=domains, execution_mode=mode)


def test_domain_execution_result_keeps_branch_outputs_isolated() -> None:
    evidence = _evidence(EvidenceDomain.EXTERNAL_FACTOR)
    result = DomainExecutionResult(
        domain=EvidenceDomain.EXTERNAL_FACTOR,
        evidence=[evidence],
        warnings=["forecast data"],
        trace_metadata={"branch": "weather"},
        success=True,
    )

    assert result.evidence == [evidence]
    assert result.errors == []
    result.model_dump_json()


def test_failed_domain_result_requires_structured_error() -> None:
    with pytest.raises(ValidationError):
        DomainExecutionResult(
            domain=EvidenceDomain.EXTERNAL_FACTOR,
            success=False,
        )


def test_aggregation_result_contains_only_structured_outputs() -> None:
    evidence = _evidence(EvidenceDomain.BUSINESS_DATA)
    result = AggregationResult(
        answer="综合回答",
        evidence=[evidence],
        warnings=["天气证据缺失"],
        trace_metadata={"aggregation_mode": "llm"},
    )

    assert result.answer == "综合回答"
    assert result.evidence[0].domain is EvidenceDomain.BUSINESS_DATA
