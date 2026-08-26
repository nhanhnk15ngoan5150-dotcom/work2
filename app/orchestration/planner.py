from app.contracts.domains import RouteDecision
from app.contracts.orchestration import ExecutionMode, ExecutionPlan


class PlanningError(ValueError):
    """The route decision cannot produce a valid execution plan."""


class DeterministicPlanner:
    # 1. 将结构化路由结果转换为执行计划
    def plan(self, decision: RouteDecision) -> ExecutionPlan:
        if not decision.selected_domains:
            raise PlanningError("Execution plan requires at least one domain")
        mode = (
            ExecutionMode.SINGLE_DOMAIN
            if len(decision.selected_domains) == 1
            else ExecutionMode.MULTI_DOMAIN
        )
        try:
            return ExecutionPlan(
                selected_domains=list(decision.selected_domains),
                execution_mode=mode,
            )
        except ValueError as exc:
            raise PlanningError("Route decision contains invalid domains") from exc
