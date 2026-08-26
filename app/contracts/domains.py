from typing import Protocol

from app.contracts.evidence import Evidence, EvidenceDomain
from app.contracts.state import AgentState


class DomainWorkflow(Protocol):
    """Common execution contract for future domain workflows."""

    @property
    def domain(self) -> EvidenceDomain: ...

    async def execute(self, state: AgentState) -> list[Evidence]: ...

