from typing import Protocol

from pydantic import BaseModel, Field

from app.contracts.evidence import EvidenceDomain
from app.contracts.state import AgentState


class RouteDecision(BaseModel):
    """Structured result produced by the deterministic fast router."""

    selected_domains: list[EvidenceDomain] = Field(default_factory=list)

    @property
    def domain(self) -> EvidenceDomain | None:
        if len(self.selected_domains) == 1:
            return self.selected_domains[0]
        return None

    @property
    def is_multi_domain(self) -> bool:
        return len(self.selected_domains) > 1


class DomainWorkflow(Protocol):
    """Common execution contract for every single-domain workflow."""

    @property
    def domain(self) -> EvidenceDomain: ...

    async def execute(self, state: AgentState) -> AgentState: ...
