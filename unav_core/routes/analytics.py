"""Route analytics: distance, source and object-type summaries.

Pure functions over a :class:`~unav_core.routes.route.Route`. Distances use the
waypoints' cached Cartesian positions (parsecs); waypoints without a position
(e.g. annotation-only) are skipped, so legs connect consecutive *positioned*
waypoints in order.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from unav_core.routes.route import Route


class RouteDistanceSummary(BaseModel):
    """Distance metrics for a route."""

    total_distance_pc: float = 0.0
    leg_count: int = 0
    positioned_waypoints: int = 0
    leg_distances_pc: list[float] = Field(default_factory=list)


def route_distance_summary(route: Route) -> RouteDistanceSummary:
    """Total and per-leg distances along the route's positioned waypoints."""
    positions = [w.position for w in route.waypoints if w.position is not None]
    legs = [positions[i].distance_to(positions[i + 1]) for i in range(len(positions) - 1)]
    return RouteDistanceSummary(
        total_distance_pc=sum(legs),
        leg_count=len(legs),
        positioned_waypoints=len(positions),
        leg_distances_pc=legs,
    )


def route_source_summary(route: Route) -> dict[str, int]:
    """Count waypoints by their (optional) source label."""
    return dict(Counter(w.source for w in route.waypoints if w.source))


def route_object_type_summary(route: Route) -> dict[str, int]:
    """Count waypoints by their (optional) object type."""
    return dict(Counter(w.object_type.value for w in route.waypoints if w.object_type is not None))
