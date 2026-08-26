import pytest

from app.contracts.domains import RouteDecision
from app.contracts.evidence import EvidenceDomain
from app.contracts.orchestration import ExecutionMode
from app.orchestration.planner import DeterministicPlanner, PlanningError


def test_planner_keeps_single_domain_short_path_plan() -> None:
    plan = DeterministicPlanner().plan(
        RouteDecision(selected_domains=[EvidenceDomain.BUSINESS_DATA])
    )

    assert plan.execution_mode is ExecutionMode.SINGLE_DOMAIN
    assert plan.selected_domains == [EvidenceDomain.BUSINESS_DATA]


def test_planner_builds_selective_multi_domain_plan() -> None:
    plan = DeterministicPlanner().plan(
        RouteDecision(
            selected_domains=[
                EvidenceDomain.BUSINESS_DATA,
                EvidenceDomain.EXTERNAL_FACTOR,
                EvidenceDomain.KNOWLEDGE_OPERATION,
            ]
        )
    )

    assert plan.execution_mode is ExecutionMode.MULTI_DOMAIN
    assert plan.selected_domains == [
        EvidenceDomain.BUSINESS_DATA,
        EvidenceDomain.EXTERNAL_FACTOR,
        EvidenceDomain.KNOWLEDGE_OPERATION,
    ]


def test_planner_rejects_empty_or_duplicate_domains() -> None:
    planner = DeterministicPlanner()

    with pytest.raises(PlanningError):
        planner.plan(RouteDecision())
    with pytest.raises(PlanningError):
        planner.plan(
            RouteDecision(
                selected_domains=[
                    EvidenceDomain.BUSINESS_DATA,
                    EvidenceDomain.BUSINESS_DATA,
                ]
            )
        )
