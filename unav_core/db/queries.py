"""High-level query functions over the local cache.

Each returns a list of rehydrated :class:`~unav_core.data.schema.CatalogObject`.
Filters and ordering are expressed against the indexed ``objects`` columns so
queries stay fast on a bounded local working set.
"""

from __future__ import annotations

from typing import Any

from unav_core.data.object_types import ObjectType
from unav_core.data.schema import CatalogObject
from unav_core.db.database import Database
from unav_core.db.schema import objects_table

_DEFAULT_LIMIT = 50
_DEFAULT_TOP_N = 10


def search_by_name(db: Database, query: str, *, limit: int = _DEFAULT_LIMIT) -> list[CatalogObject]:
    """Return objects whose ``name`` contains ``query`` (case-insensitive)."""
    cols = objects_table.c
    return db.fetch_objects(
        where=cols.name.is_not(None) & cols.name.ilike(f"%{query}%"),
        order_by=cols.name,
        limit=limit,
    )


def get_object(db: Database, uid: str) -> CatalogObject | None:
    """Return the object with the given ``uid``, or ``None`` if absent."""
    results = db.fetch_objects(where=objects_table.c.uid == uid, limit=1)
    return results[0] if results else None


def filter_by_source(
    db: Database, source: str, *, limit: int = _DEFAULT_LIMIT
) -> list[CatalogObject]:
    """Return objects from a given ``source``."""
    cols = objects_table.c
    return db.fetch_objects(where=cols.source == source, order_by=cols.uid, limit=limit)


def filter_by_type(
    db: Database, object_type: ObjectType | str, *, limit: int = _DEFAULT_LIMIT
) -> list[CatalogObject]:
    """Return objects of a given type (accepts an ``ObjectType`` or a string)."""
    value = (
        object_type.value
        if isinstance(object_type, ObjectType)
        else ObjectType.coerce(object_type).value
    )
    cols = objects_table.c
    return db.fetch_objects(where=cols.object_type == value, order_by=cols.uid, limit=limit)


def nearest_objects(
    db: Database, x: float, y: float, z: float, *, limit: int = _DEFAULT_TOP_N
) -> list[CatalogObject]:
    """Return the objects nearest to ``(x, y, z)`` (parsecs), nearest first."""
    return db.fetch_objects(
        where=_has_cartesian(),
        order_by=_squared_distance(x, y, z).asc(),
        limit=limit,
    )


def objects_within_distance(
    db: Database,
    x: float,
    y: float,
    z: float,
    max_distance_pc: float,
    *,
    limit: int | None = None,
) -> list[CatalogObject]:
    """Return objects within ``max_distance_pc`` (Euclidean) of ``(x, y, z)``.

    Uses a bounding-box prefilter on the indexed ``x/y/z`` columns, then an exact
    squared-distance test.
    """
    cols = objects_table.c
    r = max_distance_pc
    squared = _squared_distance(x, y, z)
    where = (
        _has_cartesian()
        & (cols.x >= x - r)
        & (cols.x <= x + r)
        & (cols.y >= y - r)
        & (cols.y <= y + r)
        & (cols.z >= z - r)
        & (cols.z <= z + r)
        & (squared <= r * r)
    )
    return db.fetch_objects(where=where, order_by=squared.asc(), limit=limit)


def brightest_objects(db: Database, *, limit: int = _DEFAULT_TOP_N) -> list[CatalogObject]:
    """Return the brightest objects (smallest apparent magnitude first)."""
    cols = objects_table.c
    return db.fetch_objects(
        where=cols.apparent_magnitude.is_not(None),
        order_by=cols.apparent_magnitude.asc(),
        limit=limit,
    )


def highest_redshift_objects(db: Database, *, limit: int = _DEFAULT_TOP_N) -> list[CatalogObject]:
    """Return the objects with the highest redshift first."""
    cols = objects_table.c
    return db.fetch_objects(
        where=cols.redshift.is_not(None),
        order_by=cols.redshift.desc(),
        limit=limit,
    )


def objects_in_sky_box(
    db: Database,
    ra_min: float,
    ra_max: float,
    dec_min: float,
    dec_max: float,
    *,
    limit: int | None = None,
) -> list[CatalogObject]:
    """Return objects within an RA/Dec box (a plate-carrée region).

    ``ra_min > ra_max`` selects a box that wraps across the 0/360 seam. Only
    objects with both ``ra_deg`` and ``dec_deg`` are returned (ordered by RA).
    """
    cols = objects_table.c
    base = (
        cols.ra_deg.is_not(None)
        & cols.dec_deg.is_not(None)
        & (cols.dec_deg >= dec_min)
        & (cols.dec_deg <= dec_max)
    )
    if ra_min <= ra_max:
        ra_clause = (cols.ra_deg >= ra_min) & (cols.ra_deg <= ra_max)
    else:  # wrap across the 0/360 seam
        ra_clause = (cols.ra_deg >= ra_min) | (cols.ra_deg <= ra_max)
    return db.fetch_objects(where=base & ra_clause, order_by=cols.ra_deg, limit=limit)


def _has_cartesian() -> Any:
    cols = objects_table.c
    return cols.x.is_not(None) & cols.y.is_not(None) & cols.z.is_not(None)


def _squared_distance(x: float, y: float, z: float) -> Any:
    cols = objects_table.c
    return (cols.x - x) * (cols.x - x) + (cols.y - y) * (cols.y - y) + (cols.z - z) * (cols.z - z)
