from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from app.contracts.evidence import Evidence, EvidenceDomain
from app.contracts.orchestration import AgentRoute


class ClientRequestContext(BaseModel):
    """Client-supplied request metadata without trusted tenant identity."""

    model_config = ConfigDict(extra="forbid")

    session_id: str | None = Field(default=None, max_length=128)


class TenantContext(BaseModel):
    """Trusted tenant identity produced by the server-side resolver layer."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tenant_id: str = Field(min_length=1, max_length=128)


class AgentQueryRequest(ClientRequestContext):
    question: str = Field(min_length=1, max_length=2000)


class AgentQueryResponse(BaseModel):
    request_id: str
    tenant_id: str
    route: AgentRoute
    selected_domains: list[EvidenceDomain] = Field(default_factory=list)
    answer: str
    evidence: list[Evidence]
    warnings: list[str]
    errors: list[str] = Field(default_factory=list)
    trace_metadata: dict[str, JsonValue] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
    environment: str


class ErrorItem(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    request_id: str
    error: ErrorItem
