"""Pure geometric/attribute predicates used to build the visible sector.

These operate on a :class:`~unav_core.navigation.vector.Vec3` and on objects with
a Cartesian position (e.g. ``CatalogObject``). They contain no DB access — the
:mod:`unav_core.navigation.visible_sector` module composes them over DB candidates.

See ``docs/VISIBLE_SECTOR_MODEL.md``.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from unav_core.navigation.vector import Vec3

if TYPE_CHECKING:
    from collections.abc import Container

    from unav_core.data.object_types import ObjectType
    from unav_core.data.schema import CatalogObject


def object_position(obj: CatalogObject) -> Vec3 | None:
    """Return an object's Cartesian position as a ``Vec3``, or ``None`` if it lacks one."""
    if obj.x is None or obj.y is None or obj.z is None:
        return None
    return Vec3(x=obj.x, y=obj.y, z=obj.z)


def within_distance(center: Vec3, position: Vec3, near: float, far: float) -> bool:
    """True if ``position`` lies within ``[near, far]`` of ``center``."""
    distance = center.distance_to(position)
    return near <= distance <= far


def within_cone(apex: Vec3, axis: Vec3, position: Vec3, half_angle_degrees: float) -> bool:
    """True if ``position`` lies within the cone of half-angle ``half_angle_degrees``.

    The cone has its apex at ``apex`` and opens along ``axis``. A point exactly at
    the apex is considered inside.
    """
    offset = position - apex
    length = offset.length()
    if length == 0.0:
        return True
    cos_angle = max(-1.0, min(1.0, offset.dot(axis.normalized()) / length))
    return math.degrees(math.acos(cos_angle)) <= half_angle_degrees


def matches_types(obj: CatalogObject, object_types: Container[ObjectType] | None) -> bool:
    """True if ``object_types`` is ``None`` or contains the object's type."""
    return object_types is None or obj.object_type in object_types


def within_magnitude(obj: CatalogObject, max_magnitude: float | None) -> bool:
    """True if no magnitude cap is set, or the object is at least that bright."""
    if max_magnitude is None:
        return True
    return obj.apparent_magnitude is not None and obj.apparent_magnitude <= max_magnitude
