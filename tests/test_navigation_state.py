"""Tests for Vec3, NavigatorState and the navigation event model."""

import math

import pytest
from pydantic import ValidationError

from unav_core.navigation import (
    Camera,
    DatasetChangedEvent,
    EventBus,
    NavigationEventType,
    NavigationMovedEvent,
    NavigatorState,
    ObjectSelectedEvent,
    RouteChangedEvent,
    Vec3,
    VisibleSectorChangedEvent,
)

# --- Vec3 ---


def test_vec3_arithmetic() -> None:
    a = Vec3.of(1, 2, 3)
    b = Vec3.of(4, 5, 6)
    assert (a + b).as_tuple() == (5.0, 7.0, 9.0)
    assert (b - a).as_tuple() == (3.0, 3.0, 3.0)
    assert (a * 2).as_tuple() == (2.0, 4.0, 6.0)
    assert (2 * a).as_tuple() == (2.0, 4.0, 6.0)
    assert (-a).as_tuple() == (-1.0, -2.0, -3.0)
    assert a.dot(b) == 32.0
    assert a.cross(b).as_tuple() == (-3.0, 6.0, -3.0)


def test_vec3_length_and_normalize() -> None:
    assert Vec3.of(3, 4, 0).length() == 5.0
    assert Vec3.of(0, 0, 5).normalized().as_tuple() == (0.0, 0.0, 1.0)
    assert Vec3.of(0, 0, 0).distance_to(Vec3.of(0, 0, 10)) == 10.0
    with pytest.raises(ValueError):
        Vec3().normalized()  # zero-length


def test_vec3_rejects_non_finite() -> None:
    with pytest.raises(ValidationError):
        Vec3(x=float("nan"), y=0.0, z=0.0)
    with pytest.raises(ValidationError):
        Vec3(x=float("inf"), y=0.0, z=0.0)


def test_vec3_is_frozen_and_hashable() -> None:
    v = Vec3.of(1, 2, 3)
    assert hash(v) == hash(Vec3.of(1, 2, 3))
    with pytest.raises(ValidationError):
        v.x = 9.0  # frozen


# --- NavigatorState ---


def test_state_defaults() -> None:
    state = NavigatorState()
    assert state.position == Vec3()
    assert state.direction.as_tuple() == (0.0, 0.0, -1.0)
    assert state.up.as_tuple() == (0.0, 1.0, 0.0)
    assert state.fov_degrees == 60.0
    assert state.max_visible_objects == 1000
    assert state.active_dataset_ids == []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"fov_degrees": 0.0},
        {"fov_degrees": 200.0},
        {"far_distance": 0.0},
        {"near_distance": 100.0, "far_distance": 50.0},
        {"cone_angle_degrees": 0.0},
        {"max_visible_objects": 0},
        {"direction": Vec3()},
        {"up": Vec3()},
        {"bogus": 1},
    ],
)
def test_state_validation_rejects(kwargs) -> None:
    with pytest.raises(ValidationError):
        NavigatorState(**kwargs)


def test_state_serialisation_roundtrip() -> None:
    state = NavigatorState(
        position=Vec3.of(1, 2, 3),
        direction=Vec3.of(0, 0, -1),
        cone_angle_degrees=30.0,
        epoch="J2016.0",
        active_dataset_ids=["d1", "d2"],
    )
    restored = NavigatorState.model_validate(state.model_dump())
    assert restored == state


def test_state_camera_roundtrip() -> None:
    camera = Camera(position=Vec3.of(0, 0, 10), forward=Vec3.of(0, 0, -1))
    state = NavigatorState.from_camera(camera, fov_degrees=50.0, far_distance=200.0)
    assert state.position == camera.position
    assert state.direction == camera.forward
    rebuilt = state.to_camera()
    assert rebuilt.position == camera.position
    assert rebuilt.forward == camera.forward


def test_state_forward_is_normalised() -> None:
    state = NavigatorState(direction=Vec3.of(0, 0, -10))
    assert math.isclose(state.forward().length(), 1.0)


# --- events ---


def test_event_types() -> None:
    assert (
        NavigationMovedEvent(position=Vec3(), direction=Vec3.of(0, 0, -1)).type
        is NavigationEventType.NAVIGATION_MOVED
    )
    assert VisibleSectorChangedEvent(visible_count=3).type is (
        NavigationEventType.VISIBLE_SECTOR_CHANGED
    )
    assert DatasetChangedEvent(active_dataset_ids=["a"]).type is NavigationEventType.DATASET_CHANGED
    assert ObjectSelectedEvent(uid="gaia:1").type is NavigationEventType.OBJECT_SELECTED
    assert RouteChangedEvent(route_id="r1").type is NavigationEventType.ROUTE_CHANGED


def test_event_serialises() -> None:
    event = ObjectSelectedEvent(uid="gaia:42")
    dumped = event.model_dump(mode="json")
    assert dumped["type"] == "object_selected"
    assert dumped["uid"] == "gaia:42"


def test_event_bus_dispatch() -> None:
    bus = EventBus()
    seen: list[str] = []
    typed: list[str] = []
    bus.subscribe(lambda e: seen.append(e.type.value))
    bus.subscribe_type(NavigationEventType.OBJECT_SELECTED, lambda e: typed.append(e.uid))

    bus.emit(NavigationMovedEvent(position=Vec3(), direction=Vec3.of(0, 0, -1)))
    bus.emit(ObjectSelectedEvent(uid="x"))

    assert seen == ["navigation_moved", "object_selected"]
    assert typed == ["x"]  # only the object-selected handler fired for its type


def test_event_bus_clear() -> None:
    bus = EventBus()
    hits: list[str] = []
    bus.subscribe(lambda e: hits.append(e.type.value))
    bus.clear()
    bus.emit(ObjectSelectedEvent(uid="x"))
    assert hits == []
