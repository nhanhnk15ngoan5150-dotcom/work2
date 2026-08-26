from datetime import date

from app.domains.business.models import (
    ResolvedTimeRange,
    SalesComparison,
    SalesSummary,
    TimeRangeMode,
)
from app.domains.business.repository import BusinessDataRepository


def _change_rate(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return round((current - previous) / previous * 100, 2)


class SalesService:
    def __init__(self, repository: BusinessDataRepository) -> None:
        self._repository = repository

    # 1. 查询经营核心指标
    def get_summary(self, start_date: date, end_date: date) -> SalesSummary | None:
        aggregate = self._repository.get_sales_aggregate(start_date, end_date)
        if aggregate is None or aggregate.order_count == 0:
            return None

        return SalesSummary(
            start_date=start_date,
            end_date=end_date,
            total_sales=aggregate.total_sales,
            order_count=aggregate.order_count,
            avg_order_value=round(
                aggregate.total_sales / aggregate.order_count,
                2,
            ),
        )

    # 2. 对比最近两个完整月份
    def compare(self, time_range: ResolvedTimeRange) -> SalesComparison | None:
        if (
            time_range.mode is not TimeRangeMode.COMPARE
            or time_range.current_start is None
            or time_range.current_end is None
            or time_range.previous_start is None
            or time_range.previous_end is None
        ):
            raise ValueError("Sales comparison requires a compare time range")

        current = self.get_summary(time_range.current_start, time_range.current_end)
        previous = self.get_summary(
            time_range.previous_start,
            time_range.previous_end,
        )
        if current is None or previous is None:
            return None

        return SalesComparison(
            current=current,
            previous=previous,
            sales_change_rate=_change_rate(
                current.total_sales,
                previous.total_sales,
            ),
            order_change_rate=_change_rate(
                float(current.order_count),
                float(previous.order_count),
            ),
            avg_order_value_change_rate=_change_rate(
                current.avg_order_value,
                previous.avg_order_value,
            ),
        )
