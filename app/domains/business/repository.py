from datetime import date

from sqlalchemy import and_, distinct, func, select

from app.contracts.providers import DatabaseBackend
from app.domains.business.models import (
    DataDateRange,
    ProductPerformance,
    SalesAggregate,
    StoreAggregate,
)
from app.infrastructure.database.tables import products_table, sales_table, stores_table
from app.repositories.base import Repository
from sqlalchemy.orm import Session


class BusinessDataRepository(Repository):
    def __init__(self, backend: DatabaseBackend[Session]) -> None:
        super().__init__(backend)

    # 1. 查询真实数据日期范围
    def get_sales_date_range(self) -> DataDateRange | None:
        with self._backend.session() as session:
            row = session.execute(
                select(
                    func.min(sales_table.c.date),
                    func.max(sales_table.c.date),
                )
            ).one()

        if row[0] is None or row[1] is None:
            return None

        return DataDateRange(
            min_date=date.fromisoformat(row[0]),
            max_date=date.fromisoformat(row[1]),
        )

    # 2. 查询指定周期销售聚合
    def get_sales_aggregate(
        self,
        start_date: date,
        end_date: date,
    ) -> SalesAggregate | None:
        statement = select(
            func.sum(sales_table.c.amount),
            func.count(distinct(sales_table.c.order_id)),
        ).where(
            sales_table.c.date >= start_date.isoformat(),
            sales_table.c.date < end_date.isoformat(),
        )

        with self._backend.session() as session:
            row = session.execute(statement).one()

        if row[0] is None:
            return None

        return SalesAggregate(
            total_sales=round(float(row[0]), 2),
            order_count=int(row[1]),
        )

    def has_sales_data(self, start_date: date, end_date: date) -> bool:
        statement = (
            select(sales_table.c.order_id)
            .where(
                sales_table.c.date >= start_date.isoformat(),
                sales_table.c.date < end_date.isoformat(),
            )
            .limit(1)
        )
        with self._backend.session() as session:
            return session.scalar(statement) is not None

    # 3. 查询门店经营聚合
    def get_store_aggregates(
        self,
        start_date: date,
        end_date: date,
    ) -> list[StoreAggregate]:
        total_sales = func.coalesce(func.sum(sales_table.c.amount), 0)
        order_count = func.count(distinct(sales_table.c.order_id))
        total_quantity = func.coalesce(func.sum(sales_table.c.qty), 0)
        store_sales = stores_table.outerjoin(
            sales_table,
            and_(
                sales_table.c.store_id == stores_table.c.store_id,
                sales_table.c.date >= start_date.isoformat(),
                sales_table.c.date < end_date.isoformat(),
            ),
        )
        statement = (
            select(
                stores_table.c.store_id,
                stores_table.c.store_name,
                stores_table.c.category,
                stores_table.c.district,
                total_sales.label("total_sales"),
                order_count.label("order_count"),
                total_quantity.label("total_quantity"),
            )
            .select_from(store_sales)
            .group_by(
                stores_table.c.store_id,
                stores_table.c.store_name,
                stores_table.c.category,
                stores_table.c.district,
            )
            .order_by(total_sales.desc(), stores_table.c.store_id.asc())
        )

        with self._backend.session() as session:
            rows = session.execute(statement).all()

        return [
            StoreAggregate(
                store_id=row.store_id,
                store_name=row.store_name,
                category=row.category,
                district=row.district,
                total_sales=round(float(row.total_sales), 2),
                order_count=int(row.order_count),
                total_quantity=int(row.total_quantity),
            )
            for row in rows
        ]

    # 4. 查询指定商品经营指标
    def get_product_performance(
        self,
        product_name: str,
        start_date: date,
        end_date: date,
    ) -> ProductPerformance | None:
        product_sales = sales_table.join(
            products_table,
            sales_table.c.product_id == products_table.c.product_id,
        )
        statement = (
            select(
                products_table.c.product_id,
                products_table.c.product_name,
                products_table.c.product_category,
                func.sum(sales_table.c.amount).label("total_sales"),
                func.sum(sales_table.c.qty).label("total_quantity"),
            )
            .select_from(product_sales)
            .where(
                products_table.c.product_name == product_name,
                sales_table.c.date >= start_date.isoformat(),
                sales_table.c.date < end_date.isoformat(),
            )
            .group_by(
                products_table.c.product_id,
                products_table.c.product_name,
                products_table.c.product_category,
            )
        )

        with self._backend.session() as session:
            row = session.execute(statement).one_or_none()

        if row is None:
            return None

        return ProductPerformance(
            product_id=row.product_id,
            product_name=row.product_name,
            product_category=row.product_category,
            total_sales=round(float(row.total_sales), 2),
            total_quantity=int(row.total_quantity),
        )

    # 5. 查询商品销售排行榜
    def get_product_ranking(
        self,
        start_date: date,
        end_date: date,
    ) -> list[ProductPerformance]:
        total_sales = func.sum(sales_table.c.amount)
        product_sales = sales_table.join(
            products_table,
            sales_table.c.product_id == products_table.c.product_id,
        )
        statement = (
            select(
                products_table.c.product_id,
                products_table.c.product_name,
                products_table.c.product_category,
                total_sales.label("total_sales"),
                func.sum(sales_table.c.qty).label("total_quantity"),
            )
            .select_from(product_sales)
            .where(
                sales_table.c.date >= start_date.isoformat(),
                sales_table.c.date < end_date.isoformat(),
            )
            .group_by(
                products_table.c.product_id,
                products_table.c.product_name,
                products_table.c.product_category,
            )
            .order_by(total_sales.desc(), products_table.c.product_id.asc())
        )

        with self._backend.session() as session:
            rows = session.execute(statement).all()

        return [
            ProductPerformance(
                product_id=row.product_id,
                product_name=row.product_name,
                product_category=row.product_category,
                total_sales=round(float(row.total_sales), 2),
                total_quantity=int(row.total_quantity),
                rank=index,
            )
            for index, row in enumerate(rows, start=1)
        ]

    # 6. 查询可识别商品名称
    def list_product_names(self) -> list[str]:
        statement = select(products_table.c.product_name).order_by(
            products_table.c.product_id.asc()
        )
        with self._backend.session() as session:
            return list(session.scalars(statement).all())
