import operator
from typing import Annotated, NotRequired, TypedDict

from pydantic import JsonValue

from app.contracts.domains import RouteDecision
from app.contracts.evidence import Evidence
from app.contracts.orchestration import (
    AggregationResult,
    DomainExecutionResult,
    ExecutionPlan,
)


class MultiDomainState(TypedDict):
    """Isolated orchestration state for dynamic parallel domain execution."""

    request_id: str
    tenant_id: str
    session_id: str | None
    question: str
    route_decision: RouteDecision
    execution_plan: NotRequired[ExecutionPlan]
    domain_results: Annotated[list[DomainExecutionResult], operator.add]
    validated_evidence: NotRequired[list[Evidence]]
    validation_errors: NotRequired[list[str]]
    aggregation_result: NotRequired[AggregationResult]
    trace_metadata: NotRequired[dict[str, JsonValue]]
