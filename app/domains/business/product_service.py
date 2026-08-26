from datetime import date

from app.domains.business.models import ProductPerformance
from app.domains.business.repository import BusinessDataRepository


class ProductService:
    def __init__(self, repository: BusinessDataRepository) -> None:
        self._repository = repository

    # 1. 查询指定商品经营表现
    def get_performance(
        self,
        product_name: str,
        start_date: date,
        end_date: date,
    ) -> ProductPerformance | None:
        return self._repository.get_product_performance(
            product_name,
            start_date,
            end_date,
        )

    # 2. 查询商品经营排名
    def get_ranking(
        self,
        start_date: date,
        end_date: date,
    ) -> list[ProductPerformance]:
        return self._repository.get_product_ranking(start_date, end_date)

    # 3. 从问题中识别真实商品名称
    def find_in_question(self, question: str) -> str | None:
        product_names = sorted(
            self._repository.list_product_names(),
            key=len,
            reverse=True,
        )
        return next((name for name in product_names if name in question), None)
