from datetime import date

import pytest

from app.domains.business.repository import BusinessDataRepository
from app.domains.business.sales_service import SalesService
from app.domains.business.time_service import TimeRangeService
from app.infrastructure.database.sqlite import SQLiteBackend


@pytest.fixture
def business_repository(
    database_backend: SQLiteBackend,
) -> BusinessDataRepository:
    return BusinessDataRepository(database_backend)


@pytest.fixture
def sales_service(business_repository: BusinessDataRepository) -> SalesService:
    return SalesService(business_repository)


@pytest.mark.parametrize(
    ("start_date", "end_date", "expected"),
    [
        ("2026-05-01", "2026-06-01", (139754.0, 3806, 36.72)),
        ("2026-06-01", "2026-07-01", (132820.0, 3776, 35.17)),
        ("2026-07-01", "2026-08-01", (151572.0, 4212, 35.99)),
    ],
)
def test_verified_monthly_sales_summary(
    sales_service: SalesService,
    start_date: str,
    end_date: str,
    expected: tuple[float, int, float],
) -> None:
    result = sales_service.get_summary(
        date.fromisoformat(start_date),
        date.fromisoformat(end_date),
    )

    assert result is not None
    assert (result.total_sales, result.order_count, result.avg_order_value) == expected


def test_verified_recent_sales_comparison(
    business_repository: BusinessDataRepository,
    sales_service: SalesService,
) -> None:
    recent = TimeRangeService(business_repository).resolve("最近")

    result = sales_service.compare(recent)

    assert result.current.total_sales == 151572.0
    assert result.previous.total_sales == 132820.0
    assert result.sales_change_rate == 14.12
    assert result.order_change_rate == 11.55
    assert result.avg_order_value_change_rate == 2.33


def test_sales_summary_returns_none_outside_data_range(
    sales_service: SalesService,
) -> None:
    result = sales_service.get_summary(date(2026, 4, 1), date(2026, 5, 1))

    assert result is None
