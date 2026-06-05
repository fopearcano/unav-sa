"""A tiny immutable 3D vector for the navigation layer.

Pure-Python (no numpy/astropy) so the camera and navigation state stay light and
DCC-independent. ``Vec3`` is a frozen pydantic model, so it serialises cleanly as
part of :class:`~unav_core.navigation.state.NavigatorState` and the event model.

Distances/positions are in the same units as ``CatalogObject`` Cartesian
coordinates — **parsecs** (see ``docs/COORDINATE_CONVENTIONS.md``).
"""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, field_validator


class Vec3(BaseModel):
    """An immutable 3D vector with the vector ops the camera/navigation need."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    @field_validator("x", "y", "z")
    @classmethod
    def _finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("vector components must be finite")
        return float(value)

    @classmethod
    def of(cls, x: float, y: float, z: float) -> Vec3:
        """Positional constructor: ``Vec3.of(1, 2, 3)``."""
        return cls(x=float(x), y=float(y), z=float(z))

    def __add__(self, other: Vec3) -> Vec3:
        return Vec3(x=self.x + other.x, y=self.y + other.y, z=self.z + other.z)

    def __sub__(self, other: Vec3) -> Vec3:
        return Vec3(x=self.x - other.x, y=self.y - other.y, z=self.z - other.z)

    def __neg__(self) -> Vec3:
        return Vec3(x=-self.x, y=-self.y, z=-self.z)

    def __mul__(self, scalar: float) -> Vec3:
        return Vec3(x=self.x * scalar, y=self.y * scalar, z=self.z * scalar)

    __rmul__ = __mul__

    def scale(self, scalar: float) -> Vec3:
        return self * scalar

    def dot(self, other: Vec3) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: Vec3) -> Vec3:
        return Vec3(
            x=self.y * other.z - self.z * other.y,
            y=self.z * other.x - self.x * other.z,
            z=self.x * other.y - self.y * other.x,
        )

    def length_squared(self) -> float:
        return self.dot(self)

    def length(self) -> float:
        return math.sqrt(self.length_squared())

    def normalized(self) -> Vec3:
        length = self.length()
        if length == 0.0:
            raise ValueError("cannot normalize a zero-length vector")
        return Vec3(x=self.x / length, y=self.y / length, z=self.z / length)

    def distance_to(self, other: Vec3) -> float:
        return (self - other).length()

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)
