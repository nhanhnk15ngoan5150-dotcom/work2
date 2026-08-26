from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.evidence import Evidence


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
    route: Literal["BUSINESS_DATA"]
    answer: str
    evidence: list[Evidence]
    warnings: list[str]


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
