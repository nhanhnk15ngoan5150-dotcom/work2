from datetime import date

from app.domains.business.product_service import ProductService
from app.domains.business.repository import BusinessDataRepository
from app.infrastructure.database.sqlite import SQLiteBackend


def test_verified_june_cola_performance(
    database_backend: SQLiteBackend,
) -> None:
    service = ProductService(BusinessDataRepository(database_backend))

    result = service.get_performance(
        "可乐",
        date(2026, 6, 1),
        date(2026, 7, 1),
    )

    assert result is not None
    assert result.product_name == "可乐"
    assert result.total_sales == 1550.0
    assert result.total_quantity == 310


def test_verified_july_product_ranking(
    database_backend: SQLiteBackend,
) -> None:
    service = ProductService(BusinessDataRepository(database_backend))

    result = service.get_ranking(date(2026, 7, 1), date(2026, 8, 1))

    assert len(result) == 20
    assert [
        (item.product_name, item.total_sales, item.total_quantity)
        for item in result[:3]
    ] == [
        ("三文鱼poke", 14478.0, 381),
        ("牛肉poke", 13314.0, 317),
        ("鸡肉poke", 12852.0, 378),
    ]


def test_unknown_product_returns_no_performance(
    database_backend: SQLiteBackend,
) -> None:
    service = ProductService(BusinessDataRepository(database_backend))

    result = service.get_performance(
        "不存在商品",
        date(2026, 7, 1),
        date(2026, 8, 1),
    )

    assert result is None
