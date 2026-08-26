from datetime import date

from app.domains.business.models import StorePerformance
from app.domains.business.repository import BusinessDataRepository


class StoreService:
    def __init__(self, repository: BusinessDataRepository) -> None:
        self._repository = repository

    # 1. 生成门店经营排名
    def get_ranking(
        self,
        start_date: date,
        end_date: date,
    ) -> list[StorePerformance]:
        aggregates = self._repository.get_store_aggregates(start_date, end_date)
        return [
            StorePerformance(
                rank=index,
                **aggregate.model_dump(),
                avg_order_value=(
                    round(aggregate.total_sales / aggregate.order_count, 2)
                    if aggregate.order_count
                    else None
                ),
            )
            for index, aggregate in enumerate(aggregates, start=1)
        ]
