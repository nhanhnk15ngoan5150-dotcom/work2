from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.contracts.providers import DatabaseBackend


class SQLiteBackend(DatabaseBackend[Session]):
    """SQLite adapter that owns SQLAlchemy Session lifecycle."""

    def __init__(self, database_url: str) -> None:
        if make_url(database_url).get_backend_name() != "sqlite":
            raise ValueError("SQLiteBackend requires a sqlite database URL")

        # 1. 创建数据库引擎
        self._engine = create_engine(database_url)
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
            database_session.commit()
        except Exception:
            database_session.rollback()
            raise
        finally:
            database_session.close()

    def dispose(self) -> None:
        self._engine.dispose()
