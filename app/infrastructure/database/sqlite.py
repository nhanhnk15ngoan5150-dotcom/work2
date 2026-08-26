from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
import sqlite3

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.contracts.providers import DatabaseBackend


class SQLiteBackend(DatabaseBackend[Session]):
    """SQLite adapter that owns SQLAlchemy Session lifecycle."""

    def __init__(self, database_url: str) -> None:
        url = make_url(database_url)
        if url.get_backend_name() != "sqlite":
            raise ValueError("SQLiteBackend requires a sqlite database URL")
        if not url.database or url.database == ":memory:":
            raise ValueError("Read-only SQLiteBackend requires a database file")

        # 1. 以只读模式创建数据库引擎
        database_path = Path(url.database).resolve()
        if not database_path.is_file():
            raise FileNotFoundError(f"SQLite database does not exist: {database_path}")

        def connect_read_only() -> sqlite3.Connection:
            connection = sqlite3.connect(
                f"{database_path.as_uri()}?mode=ro",
                uri=True,
                check_same_thread=False,
            )
            connection.execute("PRAGMA query_only = ON")
            return connection

        self._engine = create_engine("sqlite+pysqlite://", creator=connect_read_only)
        self._session_factory = sessionmaker(
            bind=self._engine,
            class_=Session,
            expire_on_commit=False,
        )

    @property
    def engine(self) -> Engine:
        return self._engine

    # 2. 管理数据库会话
    @contextmanager
    def session(self) -> Iterator[Session]:
        database_session = self._session_factory()
        try:
            yield database_session
        except Exception:
            database_session.rollback()
            raise
        finally:
            database_session.rollback()
            database_session.close()

    def dispose(self) -> None:
        self._engine.dispose()
