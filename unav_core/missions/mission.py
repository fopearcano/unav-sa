"""Mission: a route plus timing, per-waypoint camera settings, notes and tags.

A mission turns a :class:`~unav_core.routes.route.Route` into a reproducible,
playable voyage. Each :class:`MissionSegment` pairs a route waypoint with an
optional camera pose (a :class:`~unav_core.navigation.state.NavigatorState`) and
timing: ``transition_seconds`` (time to travel to it) and ``hold_seconds`` (dwell).

The first segment's ``transition_seconds`` is ignored (nothing precedes it).

See ``docs/MISSIONS.md``.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from unav_core.navigation.state import NavigatorState
from unav_core.routes.route import Route


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex


class MissionSegment(BaseModel):
    """One timed step of a mission: a waypoint, an optional camera, and durations."""

    model_config = ConfigDict(extra="forbid")

    waypoint_id: str
    camera: NavigatorState | None = None
    transition_seconds: float = Field(default=0.0, ge=0.0)
    hold_seconds: float = Field(default=0.0, ge=0.0)
    note: str | None = None


class Mission(BaseModel):
    """A playable voyage over a route, with timing and per-waypoint cameras."""

    model_config = ConfigDict(extra="forbid")

    mission_id: str = Field(default_factory=_new_id)
    title: str
    description: str = ""
    route: Route
    segments: list[MissionSegment] = Field(default_factory=list)
    notes: str = ""
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _segments_reference_route(self) -> Mission:
        valid_ids = {w.wid for w in self.route.waypoints}
        for segment in self.segments:
            if segment.waypoint_id not in valid_ids:
                raise ValueError(f"segment references unknown waypoint_id {segment.waypoint_id!r}")
        return self

    @property
    def total_duration_seconds(self) -> float:
        """Total timeline length (the first segment's transition is excluded)."""
        holds = sum(segment.hold_seconds for segment in self.segments)
        transitions = sum(segment.transition_seconds for segment in self.segments[1:])
        return holds + transitions

    def has_cameras(self) -> bool:
        """True if there is at least one segment and every segment has a camera."""
        return bool(self.segments) and all(s.camera is not None for s in self.segments)

    @classmethod
    def build(
        cls,
        route: Route,
        *,
        title: str,
        cameras: dict[str, NavigatorState] | None = None,
        transition_seconds: float = 10.0,
        hold_seconds: float = 0.0,
        **kwargs: Any,
    ) -> Mission:
        """Build a mission with one segment per route waypoint (in order)."""
        cameras = cameras or {}
        segments = [
            MissionSegment(
                waypoint_id=waypoint.wid,
                camera=cameras.get(waypoint.wid),
                transition_seconds=0.0 if index == 0 else transition_seconds,
                hold_seconds=hold_seconds,
            )
            for index, waypoint in enumerate(route.waypoints)
        ]
        return cls(title=title, route=route, segments=segments, **kwargs)

    def to_json(self, *, indent: int | None = 2) -> str:
        return self.model_dump_json(indent=indent)

    @classmethod
    def from_json(cls, text: str) -> Mission:
        return cls.model_validate_json(text)
