from sqlalchemy.orm import Session

from app.contracts.providers import DatabaseBackend


class Repository:
    """Base boundary for repositories backed by SQLAlchemy Sessions."""

    def __init__(self, backend: DatabaseBackend[Session]) -> None:
        self._backend = backend
