from fastapi import APIRouter, Request

from app.contracts.api import AgentQueryRequest, AgentQueryResponse
from app.contracts.evidence import EvidenceDomain
from app.contracts.state import AgentState
from app.core.exceptions import AppException
from app.core.tenant import resolve_default_tenant_context
from app.routing.fast_router import FastRouter
from app.workflows.business_data import BusinessDataWorkflow

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


@router.post("/query", response_model=AgentQueryResponse)
async def query_agent(payload: AgentQueryRequest, request: Request) -> AgentQueryResponse:
    # 1. 解析租户和快速路由
    tenant_context = resolve_default_tenant_context(request.app.state.settings)
    fast_router: FastRouter = request.app.state.fast_router
    selected_domain = fast_router.route(payload.question)
    if selected_domain is not EvidenceDomain.BUSINESS_DATA:
        raise AppException(
            code="UNSUPPORTED_QUERY",
            message="Batch 2 only supports business data questions",
            status_code=400,
        )

    # 2. 执行经营数据工作流
    state: AgentState = {
        "request_id": request.state.request_id,
        "tenant_id": tenant_context.tenant_id,
        "session_id": payload.session_id,
        "question": payload.question,
        "normalized_question": payload.question,
        "selected_domains": [EvidenceDomain.BUSINESS_DATA],
        "evidence": [],
        "errors": [],
        "warnings": [],
        "final_answer": None,
        "trace_metadata": {},
    }
    workflow: BusinessDataWorkflow = request.app.state.business_data_workflow
    result = await workflow.run(state)

    return AgentQueryResponse(
        request_id=result["request_id"],
        tenant_id=result["tenant_id"],
        route="BUSINESS_DATA",
        answer=result["final_answer"] or "没有查询到经营数据",
        evidence=result["evidence"],
        warnings=result["warnings"],
    )
