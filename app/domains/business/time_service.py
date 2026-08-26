import re
from calendar import monthrange
from datetime import date, timedelta

from app.domains.business.models import ResolvedTimeRange, TimeRangeMode
from app.domains.business.repository import BusinessDataRepository

MONTH_MAP = {
    "一月": 1,
    "1月": 1,
    "二月": 2,
    "2月": 2,
    "三月": 3,
    "3月": 3,
    "四月": 4,
    "4月": 4,
    "五月": 5,
    "5月": 5,
    "六月": 6,
    "6月": 6,
    "七月": 7,
    "7月": 7,
    "八月": 8,
    "8月": 8,
    "九月": 9,
    "9月": 9,
    "十月": 10,
    "10月": 10,
    "十一月": 11,
    "11月": 11,
    "十二月": 12,
    "12月": 12,
}


def _add_months(month_start: date, offset: int) -> date:
    month_index = month_start.year * 12 + month_start.month - 1 + offset
    return date(month_index // 12, month_index % 12 + 1, 1)


class TimeRangeService:
    def __init__(self, repository: BusinessDataRepository) -> None:
        self._repository = repository

    # 1. 解析数据驱动时间范围
    def resolve(self, expression: str | None) -> ResolvedTimeRange:
        data_range = self._repository.get_sales_date_range()
        if data_range is None:
            return ResolvedTimeRange(mode=TimeRangeMode.UNKNOWN)

        if not expression:
            return ResolvedTimeRange(
                mode=TimeRangeMode.ALL,
                start_date=data_range.min_date,
                end_date=data_range.max_date + timedelta(days=1),
            )

        normalized = str(expression).strip().replace(" ", "")
        if normalized == "最近":
            return self._resolve_recent(
                data_range.min_date,
                data_range.max_date,
            )

        explicit_match = re.fullmatch(r"(\d{4})年(.+)", normalized)
        if explicit_match:
            month = MONTH_MAP.get(explicit_match.group(2))
            if month is None:
                return ResolvedTimeRange(mode=TimeRangeMode.UNKNOWN)
            return self._resolve_month(
                int(explicit_match.group(1)),
                month,
                data_range.min_date,
                data_range.max_date,
            )

        month = MONTH_MAP.get(normalized)
        if month is None:
            return ResolvedTimeRange(mode=TimeRangeMode.UNKNOWN)

        for year in range(data_range.max_date.year, data_range.min_date.year - 1, -1):
            resolved = self._resolve_month(
                year,
                month,
                data_range.min_date,
                data_range.max_date,
            )
            if resolved.mode is TimeRangeMode.MONTH:
                return resolved

        return self._out_of_range(
            date(data_range.max_date.year, month, 1),
            data_range.min_date,
            data_range.max_date,
        )

    # 2. 解析月份边界
    def _resolve_month(
        self,
        year: int,
        month: int,
        available_start: date,
        available_end: date,
    ) -> ResolvedTimeRange:
        start_date = date(year, month, 1)
        end_date = _add_months(start_date, 1)
        if end_date > available_start and start_date <= available_end:
            return ResolvedTimeRange(
                mode=TimeRangeMode.MONTH,
                start_date=start_date,
                end_date=end_date,
            )
        return self._out_of_range(start_date, available_start, available_end)

    # 3. 解析最近完整月份
    def _resolve_recent(
        self,
        available_start: date,
        available_end: date,
    ) -> ResolvedTimeRange:
        max_date = available_end
        latest_month = date(max_date.year, max_date.month, 1)
        current_start = (
            latest_month
            if max_date.day == monthrange(max_date.year, max_date.month)[1]
            else _add_months(latest_month, -1)
        )
        current_end = _add_months(current_start, 1)
        previous_start = _add_months(current_start, -1)
        range_covers_comparison = (
            available_start <= previous_start
            and available_end >= current_end - timedelta(days=1)
        )
        if not range_covers_comparison or not self._repository.has_sales_data(
            current_start,
            current_end,
        ) or not self._repository.has_sales_data(
            previous_start,
            current_start,
        ):
            return ResolvedTimeRange(
                mode=TimeRangeMode.INSUFFICIENT_DATA,
                current_start=current_start,
                current_end=current_end,
                previous_start=previous_start,
                previous_end=current_start,
                available_start=available_start,
                available_end=available_end,
            )

        return ResolvedTimeRange(
            mode=TimeRangeMode.COMPARE,
            current_start=current_start,
            current_end=current_end,
            previous_start=previous_start,
            previous_end=current_start,
        )

    @staticmethod
    def _out_of_range(
        start_date: date,
        available_start: date,
        available_end: date,
    ) -> ResolvedTimeRange:
        return ResolvedTimeRange(
            mode=TimeRangeMode.OUT_OF_RANGE,
            start_date=start_date,
            end_date=_add_months(start_date, 1),
            available_start=available_start,
            available_end=available_end,
        )
