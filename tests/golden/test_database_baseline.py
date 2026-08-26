from hashlib import sha256
from pathlib import Path

import pytest
from sqlalchemy import func, insert, select
from sqlalchemy.exc import OperationalError

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


def test_business_database_rejects_writes_and_preserves_golden_file(
    database_backend: SQLiteBackend,
) -> None:
    database_path = Path(__file__).resolve().parents[2] / "data" / "moneki.db"
    expected_hash = "070963ba8f6c409fd09f58c8320135ed7a8c484634af0dcab397090cf62d589f"
    before_hash = sha256(database_path.read_bytes()).hexdigest()

    with pytest.raises(OperationalError, match="readonly"):
        with database_backend.session() as session:
            session.execute(
                insert(stores_table).values(
                    store_id="WRITE_TEST",
                    store_name="must-not-persist",
                )
            )

    with database_backend.session() as session:
        store_count = session.scalar(select(func.count()).select_from(stores_table))
    after_hash = sha256(database_path.read_bytes()).hexdigest()

    assert before_hash == expected_hash
    assert after_hash == expected_hash
    assert store_count == 5
