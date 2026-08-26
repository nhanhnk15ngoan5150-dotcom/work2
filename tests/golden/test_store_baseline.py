from datetime import date

from app.domains.business.repository import BusinessDataRepository
from app.domains.business.store_service import StoreService
from app.infrastructure.database.sqlite import SQLiteBackend


def test_verified_july_store_ranking(
    database_backend: SQLiteBackend,
) -> None:
    service = StoreService(BusinessDataRepository(database_backend))

    result = service.get_ranking(date(2026, 7, 1), date(2026, 8, 1))

    assert len(result) == 5
    assert [item.total_sales for item in result] == [
        32301.0,
        30951.0,
        29957.0,
        29227.0,
        29136.0,
    ]
    assert result[0].model_dump() == {
        "store_id": "S05",
        "store_name": "Super Tetsudo",
        "category": "日料",
        "district": "上海·黄浦",
        "total_sales": 32301.0,
        "order_count": 877,
        "total_quantity": 1477,
        "rank": 1,
        "avg_order_value": 36.83,
    }


def test_store_ranking_preserves_zero_sales_stores(
    database_backend: SQLiteBackend,
) -> None:
    service = StoreService(BusinessDataRepository(database_backend))

    result = service.get_ranking(date(2026, 4, 1), date(2026, 5, 1))

    assert len(result) == 5
    assert all(item.total_sales == 0 for item in result)
    assert all(item.avg_order_value is None for item in result)
