"""Engine/connection management and object fetching for the local SQLite cache.

A :class:`Database` wraps a SQLAlchemy engine bound to a SQLite file (or an
in-memory database for tests) and ensures the schema exists. It also provides
``fetch_objects`` — the shared, metadata-joining read path used by the query and
spatial-search layers, which returns rehydrated
:class:`~unav_core.data.schema.CatalogObject` instances.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, func, select
from sqlalchemy.pool import StaticPool

from unav_core.data.schema import CatalogObject
from unav_core.db.schema import (
    datasets_table,
    metadata_obj,
    metadata_table,
    objects_table,
    row_to_object,
)

PathLike = str | Path


class Database:
    """A local SQLite cache (SQLAlchemy Core) with the UNAV-SA schema applied."""

    def __init__(self, db_path: PathLike = ":memory:") -> None:
        self.db_path = str(db_path)
        self.engine = _make_engine(self.db_path)
        metadata_obj.create_all(self.engine)

    @property
    def is_memory(self) -> bool:
        return self.db_path == ":memory:"

    def connect(self) -> Any:
        """Return a SQLAlchemy connection (context manager)."""
        return self.engine.connect()

    def begin(self) -> Any:
        """Return a transactional connection (context manager)."""
        return self.engine.begin()

    def dispose(self) -> None:
        self.engine.dispose()

    def count_objects(self) -> int:
        with self.connect() as conn:
            return int(conn.execute(select(func.count()).select_from(objects_table)).scalar_one())

    def list_datasets(self) -> list[dict[str, Any]]:
        """Return the recorded datasets (one dict per row of the datasets table)."""
        with self.connect() as conn:
            rows = conn.execute(select(datasets_table)).all()
        return [dict(row._mapping) for row in rows]

    def fetch_objects(
        self,
        *,
        where: Any = None,
        order_by: Any = None,
        limit: int | None = None,
    ) -> list[CatalogObject]:
        """Fetch objects (with metadata) matching ``where``, ordered and limited."""
        join = objects_table.outerjoin(metadata_table, objects_table.c.uid == metadata_table.c.uid)
        stmt = select(objects_table, metadata_table.c.metadata_json).select_from(join)
        if where is not None:
            stmt = stmt.where(where)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        if limit is not None:
            stmt = stmt.limit(limit)

        results: list[CatalogObject] = []
        with self.connect() as conn:
            for row in conn.execute(stmt):
                mapping = row._mapping
                raw = mapping["metadata_json"]
                meta = json.loads(raw) if raw else {}
                results.append(row_to_object(mapping, meta))
        return results

    def __enter__(self) -> Database:
        return self

    def __exit__(self, *exc: object) -> None:
        self.dispose()


def _make_engine(db_path: str) -> Engine:
    if db_path == ":memory:":
        # A shared in-memory database (StaticPool) so one Database instance sees
        # its own writes across connections.
        return create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    path = Path(db_path)
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{path}")
