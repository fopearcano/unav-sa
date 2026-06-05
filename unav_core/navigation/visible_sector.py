"""Visible-sector computation: DB candidates -> distance/cone/attribute filters.

Given a :class:`~unav_core.navigation.state.NavigatorState` and a local
:class:`~unav_core.db.database.Database`, return the objects currently visible to
the navigator, sorted and capped. The pipeline (see ``docs/VISIBLE_SECTOR_MODEL.md``):

1. **DB-backed candidates** within ``far_distance`` of the camera (indexed 3D box);
2. **distance** filter to ``[near_distance, far_distance]``;
3. **cone** filter to ``cone_angle_degrees`` about the view direction;
4. optional **type** / **magnitude** filters;
5. **sort** by distance (nearest first) or magnitude (brightest first);
6. **cap** to ``max_visible_objects``.

Only objects with a Cartesian ``x/y/z`` participate (3D navigation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from unav_core.db.queries import objects_within_distance
from unav_core.navigation import filters

if TYPE_CHECKING:
    from collections.abc import Container

    from unav_core.data.object_types import ObjectType
    from unav_core.data.schema import CatalogObject
    from unav_core.db.database import Database
    from unav_core.navigation.state import NavigatorState

SORT_DISTANCE = "distance"
SORT_MAGNITUDE = "magnitude"


def visible_objects(
    db: Database,
    state: NavigatorState,
    *,
    sort: str = SORT_DISTANCE,
    object_types: Container[ObjectType] | None = None,
    max_magnitude: float | None = None,
) -> list[CatalogObject]:
    """Return the objects visible from ``state``, sorted and capped."""
    if sort not in (SORT_DISTANCE, SORT_MAGNITUDE):
        raise ValueError(f"unknown sort {sort!r}; expected {SORT_DISTANCE!r} or {SORT_MAGNITUDE!r}")

    center = state.position
    axis = state.direction
    candidates = objects_within_distance(
        db, center.x, center.y, center.z, state.far_distance, limit=None
    )

    scored: list[tuple[float, CatalogObject]] = []
    for obj in candidates:
        position = filters.object_position(obj)
        if position is None:
            continue
        if not filters.within_distance(center, position, state.near_distance, state.far_distance):
            continue
        if not filters.within_cone(center, axis, position, state.cone_angle_degrees):
            continue
        if not filters.matches_types(obj, object_types):
            continue
        if not filters.within_magnitude(obj, max_magnitude):
            continue
        scored.append((center.distance_to(position), obj))

    _sort_scored(scored, sort)
    visible = [obj for _, obj in scored]
    return visible[: state.max_visible_objects]


def _sort_scored(scored: list[tuple[float, CatalogObject]], sort: str) -> None:
    if sort == SORT_DISTANCE:
        scored.sort(key=lambda item: item[0])
    else:  # SORT_MAGNITUDE: brightest (smallest) first; missing magnitudes last.
        scored.sort(
            key=lambda item: (
                item[1].apparent_magnitude is None,
                item[1].apparent_magnitude if item[1].apparent_magnitude is not None else 0.0,
                item[0],
            )
        )
