"""Routes: planned paths through space.

Models **routes** — ordered sequences of waypoints/targets (coordinates or
catalog objects) describing a path the navigator can follow. Routes are pure
data plus planning helpers; they reference objects via the canonical
:mod:`unav_core.data` schema and are consumed by :mod:`unav_core.navigation`
and :mod:`unav_core.missions`.
"""

from unav_core.routes.analytics import (
    RouteDistanceSummary,
    route_distance_summary,
    route_object_type_summary,
    route_source_summary,
)
from unav_core.routes.route import Route
from unav_core.routes.waypoint import Waypoint, WaypointKind

__all__ = [
    "Route",
    "Waypoint",
    "WaypointKind",
    "RouteDistanceSummary",
    "route_distance_summary",
    "route_source_summary",
    "route_object_type_summary",
]
