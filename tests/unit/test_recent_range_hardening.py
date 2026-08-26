from datetime import date
from unittest.mock import Mock

from app.domains.business.models import DataDateRange, TimeRangeMode
from app.domains.business.repository import BusinessDataRepository
from app.domains.business.time_service import TimeRangeService


def test_partial_latest_month_uses_two_previous_complete_months() -> None:
    repository = Mock(spec=BusinessDataRepository)
    repository.get_sales_date_range.return_value = DataDateRange(
        min_date=date(2026, 5, 1),
        max_date=date(2026, 8, 15),
    )
    repository.has_sales_data.return_value = True

    result = TimeRangeService(repository).resolve("最近")

    assert result.mode is TimeRangeMode.COMPARE
    assert result.current_start == date(2026, 7, 1)
    assert result.current_end == date(2026, 8, 1)
    assert result.previous_start == date(2026, 6, 1)
    assert result.previous_end == date(2026, 7, 1)


def test_recent_range_reports_insufficient_comparison_data() -> None:
    repository = Mock(spec=BusinessDataRepository)
    repository.get_sales_date_range.return_value = DataDateRange(
        min_date=date(2026, 7, 1),
        max_date=date(2026, 7, 31),
    )
    repository.has_sales_data.side_effect = [True, False]

    result = TimeRangeService(repository).resolve("最近")

    assert result.mode is TimeRangeMode.INSUFFICIENT_DATA
    assert result.current_start == date(2026, 7, 1)
    assert result.previous_start == date(2026, 6, 1)


def test_recent_range_requires_available_range_to_cover_previous_month() -> None:
    repository = Mock(spec=BusinessDataRepository)
    repository.get_sales_date_range.return_value = DataDateRange(
        min_date=date(2026, 6, 15),
        max_date=date(2026, 7, 31),
    )
    repository.has_sales_data.return_value = True

    result = TimeRangeService(repository).resolve("最近")

    assert result.mode is TimeRangeMode.INSUFFICIENT_DATA
    assert result.current_start == date(2026, 7, 1)
    assert result.current_end == date(2026, 8, 1)
    assert result.previous_start == date(2026, 6, 1)
    assert result.previous_end == date(2026, 7, 1)
