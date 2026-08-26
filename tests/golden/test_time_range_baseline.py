import pytest

from app.domains.business.repository import BusinessDataRepository
from app.domains.business.time_service import TimeRangeService
from app.infrastructure.database.sqlite import SQLiteBackend


@pytest.fixture
def time_service(database_backend: SQLiteBackend) -> TimeRangeService:
    return TimeRangeService(BusinessDataRepository(database_backend))


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        (
            "五月",
            {
                "start_date": "2026-05-01",
                "end_date": "2026-06-01",
                "mode": "month",
            },
        ),
        (
            "六月",
            {
                "start_date": "2026-06-01",
                "end_date": "2026-07-01",
                "mode": "month",
            },
        ),
        (
            "七月",
            {
                "start_date": "2026-07-01",
                "end_date": "2026-08-01",
                "mode": "month",
            },
        ),
        (
            "最近",
            {
                "current_start": "2026-07-01",
                "current_end": "2026-08-01",
                "previous_start": "2026-06-01",
                "previous_end": "2026-07-01",
                "mode": "compare",
            },
        ),
    ],
)
def test_verified_time_ranges(
    time_service: TimeRangeService,
    expression: str,
    expected: dict[str, str],
) -> None:
    result = time_service.resolve(expression)

    assert result.model_dump(mode="json", exclude_none=True) == expected


@pytest.mark.parametrize("expression", ["四月", "八月"])
def test_verified_out_of_range_months(
    time_service: TimeRangeService,
    expression: str,
) -> None:
    result = time_service.resolve(expression)

    assert result.mode == "out_of_range"
    assert result.available_start.isoformat() == "2026-05-01"
    assert result.available_end.isoformat() == "2026-07-31"


def test_data_range_comes_from_database(
    database_backend: SQLiteBackend,
) -> None:
    result = BusinessDataRepository(database_backend).get_sales_date_range()

    assert result is not None
    assert result.model_dump(mode="json") == {
        "min_date": "2026-05-01",
        "max_date": "2026-07-31",
    }
