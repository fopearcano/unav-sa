"""Route: an ordered, editable sequence of waypoints with summary helpers.

A route is pure, serialisable data. Editing (add/remove/reorder) mutates the
route in place; analytics (distance, source, object-type) are delegated to
:mod:`unav_core.routes.analytics`.

See ``docs/ROUTES_AND_WAYPOINTS.md``.
"""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from unav_core.routes.analytics import (
    RouteDistanceSummary,
    route_distance_summary,
    route_object_type_summary,
    route_source_summary,
)
from unav_core.routes.waypoint import Waypoint


def _new_id() -> str:
    return uuid.uuid4().hex


class Route(BaseModel):
    """An ordered path of :class:`~unav_core.routes.waypoint.Waypoint` stops."""

    model_config = ConfigDict(extra="forbid")

    route_id: str = Field(default_factory=_new_id)
    name: str
    description: str = ""
    waypoints: list[Waypoint] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    # --- editing ---

    def add_waypoint(self, waypoint: Waypoint, index: int | None = None) -> Waypoint:
        """Append a waypoint, or insert it at ``index``."""
        if index is None:
            self.waypoints.append(waypoint)
        else:
            self.waypoints.insert(index, waypoint)
        return waypoint

    def remove_waypoint(self, wid: str) -> Waypoint:
        """Remove and return the waypoint with id ``wid`` (raises ``KeyError``)."""
        for index, waypoint in enumerate(self.waypoints):
            if waypoint.wid == wid:
                return self.waypoints.pop(index)
        raise KeyError(wid)

    def move_waypoint(self, wid: str, new_index: int) -> Waypoint:
        """Move the waypoint with id ``wid`` to ``new_index``."""
        waypoint = self.remove_waypoint(wid)
        self.waypoints.insert(new_index, waypoint)
        return waypoint

    def reorder(self, order: list[str]) -> None:
        """Reorder waypoints to match ``order`` (a permutation of existing ids)."""
        if sorted(order) != sorted(w.wid for w in self.waypoints):
            raise ValueError("reorder() requires a permutation of the existing waypoint ids")
        by_id = {w.wid: w for w in self.waypoints}
        self.waypoints = [by_id[wid] for wid in order]

    def get_waypoint(self, wid: str) -> Waypoint | None:
        for waypoint in self.waypoints:
            if waypoint.wid == wid:
                return waypoint
        return None

    def __len__(self) -> int:
        return len(self.waypoints)

    # --- analytics ---

    def distance_summary(self) -> RouteDistanceSummary:
        return route_distance_summary(self)

    def source_summary(self) -> dict[str, int]:
        return route_source_summary(self)

    def object_type_summary(self) -> dict[str, int]:
        return route_object_type_summary(self)

    # --- serialization ---

    def to_json(self, *, indent: int | None = 2) -> str:
        return self.model_dump_json(indent=indent)

    @classmethod
    def from_json(cls, text: str) -> Route:
        return cls.model_validate_json(text)
