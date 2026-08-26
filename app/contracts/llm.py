from enum import StrEnum

from pydantic import BaseModel, Field


class LLMRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class LLMMessage(BaseModel):
    role: LLMRole
    content: str = Field(min_length=1)


class LLMResponse(BaseModel):
    content: str = Field(min_length=1)
    model: str | None = None
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    latency_ms: float | None = Field(default=None, ge=0.0)
    estimated_cost: float | None = Field(default=None, ge=0.0)
