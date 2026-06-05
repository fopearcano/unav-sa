"""NavigatorState: the serialisable, validated real-time navigation state.

``NavigatorState`` is the canonical value object for where the navigator is, where
it is looking, and how the visible sector is bounded. It is a pydantic model so it
serialises for export/interchange and (future) state sync. A :class:`Camera` is
the live controller; convert between them with ``from_camera`` / ``to_camera``.

See ``docs/NAVIGATION_STATE.md`` and ``docs/NAVIGATION_ENGINE.md``.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from unav_core.navigation.camera import Camera
from unav_core.navigation.vector import Vec3


def _default_direction() -> Vec3:
    return Vec3(x=0.0, y=0.0, z=-1.0)


def _default_up() -> Vec3:
    return Vec3(x=0.0, y=1.0, z=0.0)


class NavigatorState(BaseModel):
    """Where the navigator is, where it looks, and how the visible sector is bounded."""

    model_config = ConfigDict(extra="forbid")

    position: Vec3 = Field(default_factory=Vec3, description="Camera position (pc).")
    direction: Vec3 = Field(default_factory=_default_direction, description="View direction.")
    up: Vec3 = Field(default_factory=_default_up, description="Up vector.")
    fov_degrees: float = Field(default=60.0, gt=0.0, lt=180.0, description="Field of view (deg).")
    near_distance: float = Field(default=0.0, ge=0.0, description="Near clip distance (pc).")
    far_distance: float = Field(default=1000.0, gt=0.0, description="Far clip distance (pc).")
    cone_angle_degrees: float = Field(
        default=45.0, gt=0.0, le=180.0, description="Visible-sector cone half-angle (deg)."
    )
    epoch: str | None = Field(default=None, description="Reference epoch, e.g. 'J2016.0'.")
    max_visible_objects: int = Field(default=1000, ge=1, description="Visible-object cap.")
    active_dataset_ids: list[str] = Field(
        default_factory=list, description="Active dataset ids (advisory; see docs)."
    )

    @field_validator("direction", "up")
    @classmethod
    def _non_zero(cls, value: Vec3) -> Vec3:
        if value.length_squared() == 0.0:
            raise ValueError("must be a non-zero vector")
        return value

    @model_validator(mode="after")
    def _far_beyond_near(self) -> NavigatorState:
        if self.far_distance <= self.near_distance:
            raise ValueError("far_distance must be greater than near_distance")
        return self

    def forward(self) -> Vec3:
        """The normalised view direction."""
        return self.direction.normalized()

    def to_camera(self) -> Camera:
        """Build a live :class:`Camera` from this state's pose."""
        return Camera(position=self.position, forward=self.direction, up=self.up)

    @classmethod
    def from_camera(cls, camera: Camera, **params: Any) -> NavigatorState:
        """Build a state from a camera's pose; ``params`` set the viewing fields."""
        return cls(position=camera.position, direction=camera.forward, up=camera.up, **params)
