"""Build the lightweight 3D render payload from catalog objects.

This is a *presentation* mapping for the standalone 3D viewport: each renderable
object becomes a slim :class:`~unav_server.models.RenderPoint` carrying only what
the viewport needs (id, type/source, Cartesian position, a display colour and
size, and an optional name) — **no metadata or provenance**. Full records are
fetched per-object only when one is selected (``GET /objects/{uid}``).

Colour-by-type and size-by-magnitude live here (the server side of the same
palette the 2D map uses); they are not astronomy and stay out of ``unav_core``.
"""

from __future__ import annotations

from collections.abc import Iterable

from unav_core.data.schema import CatalogObject
from unav_server.models import RenderPoint

#: Display colour per object type (matches the 2D map legend).
TYPE_COLORS: dict[str, str] = {
    "star": "#cfe8ff",
    "galaxy": "#ffd28a",
    "quasar": "#ff9bd1",
    "planet": "#9affc4",
    "moon": "#cccccc",
    "asteroid": "#bda27a",
    "comet": "#9ad0ff",
    "nebula": "#c9a8ff",
    "spacecraft": "#ff8c69",
    "custom": "#b0b0ff",
    "unknown": "#888888",
}
_DEFAULT_COLOR = "#888888"


def color_for_type(object_type: str) -> str:
    return TYPE_COLORS.get(object_type, _DEFAULT_COLOR)


def size_for_magnitude(magnitude: float | None) -> float:
    """Display size: brighter (smaller magnitude) -> larger; missing -> default."""
    if magnitude is None:
        return 2.5
    return max(1.0, min(6.0, 5.0 - magnitude / 4.0))


def render_points(objects: Iterable[CatalogObject]) -> list[RenderPoint]:
    """Map objects with a Cartesian position to slim render points."""
    points: list[RenderPoint] = []
    for obj in objects:
        if obj.x is None or obj.y is None or obj.z is None:
            continue
        type_name = obj.object_type.value
        points.append(
            RenderPoint(
                uid=obj.uid,
                source=obj.source,
                object_type=type_name,
                x=obj.x,
                y=obj.y,
                z=obj.z,
                color=color_for_type(type_name),
                size=size_for_magnitude(obj.apparent_magnitude),
                name=obj.name,
            )
        )
    return points
