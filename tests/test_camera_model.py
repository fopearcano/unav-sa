"""Tests for the Camera model (pure 3D pose control)."""

import math

import pytest

from unav_core.data import CatalogObject, ObjectType
from unav_core.navigation import Camera, Vec3


def _orthonormal(camera: Camera) -> bool:
    f, r, u = camera.forward, camera.right, camera.up
    unit = (
        math.isclose(f.length(), 1.0)
        and math.isclose(r.length(), 1.0)
        and math.isclose(u.length(), 1.0)
    )
    orthogonal = abs(f.dot(r)) < 1e-9 and abs(f.dot(u)) < 1e-9 and abs(r.dot(u)) < 1e-9
    return unit and orthogonal


def test_default_orientation() -> None:
    camera = Camera()
    assert camera.position == Vec3()
    assert camera.forward.as_tuple() == (0.0, 0.0, -1.0)
    assert camera.up.as_tuple() == (0.0, 1.0, 0.0)
    assert _orthonormal(camera)


def test_look_at_aims_forward() -> None:
    camera = Camera(position=Vec3.of(0, 0, 10))
    camera.look_at(Vec3.of(0, 0, 0))
    assert camera.forward.as_tuple() == (0.0, 0.0, -1.0)
    assert _orthonormal(camera)


def test_look_at_own_position_raises() -> None:
    camera = Camera(position=Vec3.of(1, 1, 1))
    with pytest.raises(ValueError):
        camera.look_at(Vec3.of(1, 1, 1))


def test_moves() -> None:
    camera = Camera(position=Vec3.of(0, 0, 10), forward=Vec3.of(0, 0, -1))
    camera.move_forward(5)
    assert camera.position.as_tuple() == (0.0, 0.0, 5.0)
    camera.move_right(2)  # right is +x
    assert camera.position.as_tuple() == (2.0, 0.0, 5.0)
    camera.move_up(3)  # up is +y
    assert camera.position.as_tuple() == (2.0, 3.0, 5.0)


def test_orbit_yaw() -> None:
    camera = Camera(position=Vec3.of(0, 0, 10), forward=Vec3.of(0, 0, -1))
    camera.orbit_target(Vec3.of(0, 0, 0), yaw_degrees=90.0, pitch_degrees=0.0)
    assert camera.position.as_tuple() == pytest.approx((10.0, 0.0, 0.0), abs=1e-9)
    assert camera.forward.as_tuple() == pytest.approx((-1.0, 0.0, 0.0), abs=1e-9)
    # distance to the target is preserved by an orbit
    assert math.isclose(camera.position.distance_to(Vec3()), 10.0)


def test_orbit_pitch() -> None:
    camera = Camera(position=Vec3.of(0, 0, 10), forward=Vec3.of(0, 0, -1))
    camera.orbit_target(Vec3.of(0, 0, 0), yaw_degrees=0.0, pitch_degrees=90.0)
    assert camera.position.as_tuple() == pytest.approx((0.0, -10.0, 0.0), abs=1e-9)
    assert math.isclose(camera.position.distance_to(Vec3()), 10.0)


def test_focus_object_with_distance() -> None:
    camera = Camera(position=Vec3.of(0, 0, 10), forward=Vec3.of(0, 0, -1))
    camera.focus_object(Vec3.of(0, 0, 0), distance=5.0)
    assert camera.position.as_tuple() == pytest.approx((0.0, 0.0, 5.0), abs=1e-9)
    assert math.isclose(camera.position.distance_to(Vec3()), 5.0)
    assert camera.forward.as_tuple() == pytest.approx((0.0, 0.0, -1.0), abs=1e-9)


def test_focus_object_without_distance_only_aims() -> None:
    camera = Camera(position=Vec3.of(10, 0, 0))
    camera.focus_object(Vec3.of(0, 0, 0))
    assert camera.position.as_tuple() == (10.0, 0.0, 0.0)  # unmoved
    assert camera.forward.as_tuple() == pytest.approx((-1.0, 0.0, 0.0), abs=1e-9)


def test_focus_accepts_catalog_object() -> None:
    obj = CatalogObject(uid="t", source="s", object_type=ObjectType.STAR, x=0.0, y=0.0, z=0.0)
    camera = Camera(position=Vec3.of(0, 0, 8), forward=Vec3.of(0, 0, -1))
    camera.focus_object(obj, distance=4.0)
    assert camera.position.as_tuple() == pytest.approx((0.0, 0.0, 4.0), abs=1e-9)


def test_up_parallel_to_forward_falls_back() -> None:
    # forward and up both +y: the camera must still produce an orthonormal basis.
    camera = Camera(forward=Vec3.of(0, 1, 0), up=Vec3.of(0, 1, 0))
    assert _orthonormal(camera)
    assert camera.forward.as_tuple() == pytest.approx((0.0, 1.0, 0.0), abs=1e-9)
