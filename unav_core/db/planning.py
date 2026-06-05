"""Persistence for voyage planning: bookmarks, routes and missions.

Each is stored as a JSON blob (the pydantic model) in its own table, keyed by id,
with an insertion ``created_at`` used for stable ordering. ``save_*`` is an upsert
that preserves the original ``created_at`` on update, so editing a route/mission
does not reorder it. This makes plans **persist across app restarts** (they live
in the same SQLite database as the catalog). See ``docs/ROUTES_BOOKMARKS_MISSIONS.md``.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, Table, select

from unav_core.db.database import Database
from unav_core.db.schema import bookmarks_table, missions_table, routes_table
from unav_core.missions import Mission
from unav_core.navigation.bookmarks import Bookmark
from unav_core.routes import Route


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _upsert(db: Database, table: Table, pk: Column, pk_value: str, data_json: str) -> None:
    """Insert or replace a row by primary key, preserving its ``created_at``."""
    with db.begin() as conn:
        created_at = conn.execute(
            select(table.c.created_at).where(pk == pk_value)
        ).scalar_one_or_none()
        conn.execute(table.delete().where(pk == pk_value))
        conn.execute(
            table.insert(),
            {pk.name: pk_value, "created_at": created_at or _now_iso(), "data_json": data_json},
        )


def _list_json(db: Database, table: Table) -> list[str]:
    pk = list(table.primary_key.columns)[0]
    with db.connect() as conn:
        rows = conn.execute(select(table.c.data_json).order_by(table.c.created_at, pk)).all()
    return [row[0] for row in rows]


def _get_json(db: Database, table: Table, pk: Column, pk_value: str) -> str | None:
    with db.connect() as conn:
        return conn.execute(select(table.c.data_json).where(pk == pk_value)).scalar_one_or_none()


def _delete(db: Database, table: Table, pk: Column, pk_value: str) -> bool:
    with db.begin() as conn:
        result = conn.execute(table.delete().where(pk == pk_value))
    return result.rowcount > 0


# --- bookmarks ---


def save_bookmark(db: Database, bookmark: Bookmark) -> Bookmark:
    _upsert(
        db,
        bookmarks_table,
        bookmarks_table.c.bookmark_id,
        bookmark.bookmark_id,
        bookmark.to_json(indent=None),
    )
    return bookmark


def list_bookmarks(db: Database) -> list[Bookmark]:
    return [Bookmark.model_validate_json(j) for j in _list_json(db, bookmarks_table)]


def get_bookmark(db: Database, bookmark_id: str) -> Bookmark | None:
    j = _get_json(db, bookmarks_table, bookmarks_table.c.bookmark_id, bookmark_id)
    return Bookmark.model_validate_json(j) if j else None


def delete_bookmark(db: Database, bookmark_id: str) -> bool:
    return _delete(db, bookmarks_table, bookmarks_table.c.bookmark_id, bookmark_id)


# --- routes ---


def save_route(db: Database, route: Route) -> Route:
    _upsert(db, routes_table, routes_table.c.route_id, route.route_id, route.to_json(indent=None))
    return route


def list_routes(db: Database) -> list[Route]:
    return [Route.model_validate_json(j) for j in _list_json(db, routes_table)]


def get_route(db: Database, route_id: str) -> Route | None:
    j = _get_json(db, routes_table, routes_table.c.route_id, route_id)
    return Route.model_validate_json(j) if j else None


def delete_route(db: Database, route_id: str) -> bool:
    return _delete(db, routes_table, routes_table.c.route_id, route_id)


# --- missions ---


def save_mission(db: Database, mission: Mission) -> Mission:
    _upsert(
        db,
        missions_table,
        missions_table.c.mission_id,
        mission.mission_id,
        mission.to_json(indent=None),
    )
    return mission


def list_missions(db: Database) -> list[Mission]:
    return [Mission.model_validate_json(j) for j in _list_json(db, missions_table)]


def get_mission(db: Database, mission_id: str) -> Mission | None:
    j = _get_json(db, missions_table, missions_table.c.mission_id, mission_id)
    return Mission.model_validate_json(j) if j else None


def delete_mission(db: Database, mission_id: str) -> bool:
    return _delete(db, missions_table, missions_table.c.mission_id, mission_id)
