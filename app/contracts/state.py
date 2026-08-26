from typing import TypedDict

from pydantic import JsonValue

from app.contracts.evidence import Evidence, EvidenceDomain


class AgentState(TypedDict):
    """Minimal shared state draft for the future LangGraph workflow."""

    request_id: str
    tenant_id: str
    session_id: str | None
    question: str
    normalized_question: str
    selected_domains: list[EvidenceDomain]
    evidence: list[Evidence]
    errors: list[str]
    warnings: list[str]
    final_answer: str | None
    trace_metadata: dict[str, JsonValue]
