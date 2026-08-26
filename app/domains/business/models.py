from datetime import date
from enum import StrEnum

from pydantic import BaseModel


class TimeRangeMode(StrEnum):
    ALL = "all"
    MONTH = "month"
    COMPARE = "compare"
    OUT_OF_RANGE = "out_of_range"
    UNKNOWN = "unknown"


class BusinessIntent(StrEnum):
    SALES_SUMMARY = "sales_summary"
    SALES_COMPARISON = "sales_comparison"
    STORE_RANKING = "store_ranking"
    PRODUCT_PERFORMANCE = "product_performance"
    PRODUCT_RANKING = "product_ranking"
    UNKNOWN = "unknown"


class DataDateRange(BaseModel):
    min_date: date
    max_date: date


class ResolvedTimeRange(BaseModel):
    mode: TimeRangeMode
    start_date: date | None = None
    end_date: date | None = None
    current_start: date | None = None
    current_end: date | None = None
    previous_start: date | None = None
    previous_end: date | None = None
    available_start: date | None = None
    available_end: date | None = None


class SalesAggregate(BaseModel):
    total_sales: float
    order_count: int


class SalesSummary(BaseModel):
    start_date: date
    end_date: date
    total_sales: float
    order_count: int
    avg_order_value: float


class SalesComparison(BaseModel):
    current: SalesSummary
    previous: SalesSummary
    sales_change_rate: float | None
    order_change_rate: float | None
    avg_order_value_change_rate: float | None


class StoreAggregate(BaseModel):
    store_id: str
    store_name: str
    category: str | None
    district: str | None
    total_sales: float
    order_count: int
    total_quantity: int


class StorePerformance(StoreAggregate):
    rank: int
    avg_order_value: float | None


class ProductPerformance(BaseModel):
    product_id: str
    product_name: str
    product_category: str | None
    total_sales: float
    total_quantity: int
    rank: int | None = None
