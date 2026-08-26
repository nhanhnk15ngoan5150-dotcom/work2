from fastapi import APIRouter, Request

from app.contracts.api import AgentQueryRequest, AgentQueryResponse
from app.contracts.domains import DomainWorkflow
from app.contracts.evidence import EvidenceDomain
from app.contracts.state import AgentState
from app.core.exceptions import AppException
from app.core.tenant import resolve_default_tenant_context
from app.routing.fast_router import FastRouter

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


@router.post("/query", response_model=AgentQueryResponse)
async def query_agent(payload: AgentQueryRequest, request: Request) -> AgentQueryResponse:
    # 1. 解析租户和快速路由
    tenant_context = resolve_default_tenant_context(request.app.state.settings)
    fast_router: FastRouter = request.app.state.fast_router
    route_decision = fast_router.decide(payload.question)
    if route_decision.is_multi_domain:
        raise AppException(
            code="MULTI_DOMAIN_REQUIRES_PLANNER",
            message="Multi-domain query requires planner execution",
            status_code=400,
        )

    selected_domain = route_decision.domain
    if selected_domain is None:
        raise AppException(
            code="UNSUPPORTED_QUERY",
            message="No supported domain matched the question",
            status_code=400,
        )

    domain_workflows: dict[EvidenceDomain, DomainWorkflow] = (
        request.app.state.domain_workflows
    )
    workflow = domain_workflows.get(selected_domain)
    if workflow is None:
        raise AppException(
            code="DOMAIN_NOT_CONFIGURED",
            message=f"Domain workflow is not configured: {selected_domain.value}",
            status_code=503,
        )

    # 2. 执行单领域工作流
    state: AgentState = {
        "request_id": request.state.request_id,
        "tenant_id": tenant_context.tenant_id,
        "session_id": payload.session_id,
        "question": payload.question,
        "normalized_question": payload.question,
        "selected_domains": [selected_domain],
        "evidence": [],
        "errors": [],
        "warnings": [],
        "final_answer": None,
        "trace_metadata": {},
    }
    result = await workflow.execute(state)

    return AgentQueryResponse(
        request_id=result["request_id"],
        tenant_id=result["tenant_id"],
        route=selected_domain,
        answer=result["final_answer"] or "没有查询到经营数据",
        evidence=result["evidence"],
        warnings=[*result["warnings"], *result["errors"]],
    )
