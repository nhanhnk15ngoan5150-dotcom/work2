from sqlalchemy import func, select

from app.infrastructure.database.sqlite import SQLiteBackend
from app.infrastructure.database.tables import products_table, sales_table, stores_table


def test_copied_database_matches_verified_baseline(
    database_backend: SQLiteBackend,
) -> None:
    with database_backend.session() as session:
        sales_baseline = session.execute(
            select(
                func.min(sales_table.c.date),
                func.max(sales_table.c.date),
                func.count(),
            ).select_from(sales_table)
        ).one()
        store_count = session.scalar(select(func.count()).select_from(stores_table))
        product_count = session.scalar(
            select(func.count()).select_from(products_table)
        )

    assert sales_baseline == ("2026-05-01", "2026-07-31", 11944)
    assert store_count == 5
    assert product_count == 20


def test_sqlite_backend_provides_sqlalchemy_session(
    database_backend: SQLiteBackend,
) -> None:
    with database_backend.session() as session:
        assert session.bind is database_backend.engine
