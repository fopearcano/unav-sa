"""Camera model: a live, mutable controller over a 3D pose (position + orientation).

The camera keeps an orthonormal ``forward``/``up``/``right`` basis and offers the
usual navigation moves. It is pure geometry (no DB, no astropy) and is converted
to/from the serialisable :class:`~unav_core.navigation.state.NavigatorState` by
that class (``NavigatorState.from_camera`` / ``NavigatorState.to_camera``).

See ``docs/NAVIGATION_STATE.md``.
"""

from __future__ import annotations

import math

from unav_core.navigation.vector import Vec3

_WORLD_UP = Vec3(x=0.0, y=1.0, z=0.0)
_DEFAULT_FORWARD = Vec3(x=0.0, y=0.0, z=-1.0)
_ALT_UP = Vec3(x=1.0, y=0.0, z=0.0)


def _to_vec3(target: object) -> Vec3:
    """Accept a :class:`Vec3` or anything with finite ``x``/``y``/``z`` (e.g. a CatalogObject)."""
    if isinstance(target, Vec3):
        return target
    x = getattr(target, "x", None)
    y = getattr(target, "y", None)
    z = getattr(target, "z", None)
    if x is None or y is None or z is None:
        raise ValueError("target must be a Vec3 or have x/y/z (e.g. an object with a 3D position)")
    return Vec3(x=float(x), y=float(y), z=float(z))


def _rotate(vector: Vec3, axis: Vec3, angle_rad: float) -> Vec3:
    """Rotate ``vector`` about ``axis`` by ``angle_rad`` (Rodrigues' formula)."""
    k = axis.normalized()
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    return vector * cos_a + k.cross(vector) * sin_a + k * (k.dot(vector) * (1.0 - cos_a))


class Camera:
    """A position and an orthonormal orientation you can move and aim."""

    def __init__(
        self, position: Vec3 | None = None, forward: Vec3 | None = None, up: Vec3 | None = None
    ) -> None:
        self.position = position if position is not None else Vec3()
        self._set_orientation(
            forward if forward is not None else _DEFAULT_FORWARD,
            up if up is not None else _WORLD_UP,
        )

    @property
    def forward(self) -> Vec3:
        return self._forward

    @property
    def up(self) -> Vec3:
        return self._up

    @property
    def right(self) -> Vec3:
        return self._right

    def _set_orientation(self, forward: Vec3, up: Vec3) -> None:
        f = forward.normalized()
        right = f.cross(up)
        if right.length_squared() == 0.0:
            # 'up' is parallel to 'forward'; choose a stable fallback up.
            fallback = _WORLD_UP if abs(f.dot(_WORLD_UP)) < 0.999 else _ALT_UP
            right = f.cross(fallback)
        right = right.normalized()
        self._forward = f
        self._right = right
        self._up = right.cross(f).normalized()

    def look_at(self, target: object, up_hint: Vec3 | None = None) -> Camera:
        """Aim ``forward`` at ``target`` (a Vec3 or object with x/y/z)."""
        point = _to_vec3(target)
        direction = point - self.position
        if direction.length_squared() == 0.0:
            raise ValueError("cannot look at the camera's own position")
        self._set_orientation(direction, up_hint if up_hint is not None else self._up)
        return self

    def move_forward(self, distance: float) -> Camera:
        self.position = self.position + self._forward * distance
        return self

    def move_right(self, distance: float) -> Camera:
        self.position = self.position + self._right * distance
        return self

    def move_up(self, distance: float) -> Camera:
        self.position = self.position + self._up * distance
        return self

    def orbit_target(self, target: object, yaw_degrees: float, pitch_degrees: float) -> Camera:
        """Orbit around ``target`` by ``yaw`` (about up) and ``pitch`` (about right)."""
        point = _to_vec3(target)
        offset = self.position - point
        if offset.length_squared() == 0.0:
            raise ValueError("cannot orbit around the camera's own position")
        offset = _rotate(offset, self._up, math.radians(yaw_degrees))
        offset = _rotate(offset, self._right, math.radians(pitch_degrees))
        self.position = point + offset
        self.look_at(point)
        return self

    def focus_object(self, target: object, distance: float | None = None) -> Camera:
        """Aim at ``target``; if ``distance`` is given, sit that far away along the view."""
        point = _to_vec3(target)
        if distance is None:
            return self.look_at(point)
        direction = point - self.position
        view = self._forward if direction.length_squared() == 0.0 else direction.normalized()
        self.position = point - view * distance
        self._set_orientation(point - self.position, self._up)
        return self
