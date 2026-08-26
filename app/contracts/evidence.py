from datetime import datetime, timezone
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class EvidenceDomain(StrEnum):
    BUSINESS_DATA = "BUSINESS_DATA"
    EXTERNAL_FACTOR = "EXTERNAL_FACTOR"
    KNOWLEDGE_OPERATION = "KNOWLEDGE_OPERATION"


class EvidenceType(StrEnum):
    FACT = "FACT"
    CORRELATION = "CORRELATION"
    HYPOTHESIS = "HYPOTHESIS"
    PREDICTION = "PREDICTION"
    RECOMMENDATION = "RECOMMENDATION"


class Evidence(BaseModel):
    """Shared output contract for every future domain workflow."""

    model_config = ConfigDict(allow_inf_nan=False)

    evidence_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str = Field(min_length=1, max_length=128)
    domain: EvidenceDomain
    evidence_type: EvidenceType
    claim: str = Field(min_length=1)
    value: JsonValue = None
    unit: str | None = None
    source_type: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    sample_size: int | None = Field(default=None, ge=0)
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
