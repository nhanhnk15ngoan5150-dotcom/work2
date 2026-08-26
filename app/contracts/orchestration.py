from enum import StrEnum

from pydantic import BaseModel, Field, JsonValue, model_validator

from app.contracts.evidence import Evidence, EvidenceDomain


class ExecutionMode(StrEnum):
    SINGLE_DOMAIN = "SINGLE_DOMAIN"
    MULTI_DOMAIN = "MULTI_DOMAIN"


class AgentRoute(StrEnum):
    BUSINESS_DATA = EvidenceDomain.BUSINESS_DATA.value
    EXTERNAL_FACTOR = EvidenceDomain.EXTERNAL_FACTOR.value
    KNOWLEDGE_OPERATION = EvidenceDomain.KNOWLEDGE_OPERATION.value
    MULTI_DOMAIN = "MULTI_DOMAIN"

    @classmethod
    def from_domain(cls, domain: EvidenceDomain) -> "AgentRoute":
        return cls(domain.value)


class ExecutionPlan(BaseModel):
    selected_domains: list[EvidenceDomain] = Field(min_length=1)
    execution_mode: ExecutionMode

    @model_validator(mode="after")
    def validate_domain_count(self) -> "ExecutionPlan":
        if len(set(self.selected_domains)) != len(self.selected_domains):
            raise ValueError("Execution plan domains must be unique")
        if (
            self.execution_mode is ExecutionMode.SINGLE_DOMAIN
            and len(self.selected_domains) != 1
        ):
            raise ValueError("Single-domain plan requires exactly one domain")
        if (
            self.execution_mode is ExecutionMode.MULTI_DOMAIN
            and len(self.selected_domains) < 2
        ):
            raise ValueError("Multi-domain plan requires at least two domains")
        return self


class DomainExecutionResult(BaseModel):
    domain: EvidenceDomain
    evidence: list[Evidence] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    trace_metadata: dict[str, JsonValue] = Field(default_factory=dict)
    success: bool

    @model_validator(mode="after")
    def validate_success(self) -> "DomainExecutionResult":
        if self.success and self.errors:
            raise ValueError("Successful domain result cannot contain errors")
        if not self.success and not self.errors:
            raise ValueError("Failed domain result requires an error")
        return self


class AggregationResult(BaseModel):
    answer: str = Field(min_length=1)
    evidence: list[Evidence] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    trace_metadata: dict[str, JsonValue] = Field(default_factory=dict)


class EvidenceValidationResult(BaseModel):
    evidence: list[Evidence] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
