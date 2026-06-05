"""Tests for visible-sector computation (cone/distance/cap/sort over DB candidates)."""

import pytest

from unav_core.data import CatalogObject, ObjectType
from unav_core.db import Database, import_objects
from unav_core.navigation import NavigatorState, Vec3, visible_objects


def _objects() -> list[CatalogObject]:
    return [
        # On-axis in front (forward = -z), 10 pc away.
        CatalogObject(
            uid="A",
            source="t",
            object_type=ObjectType.STAR,
            x=0,
            y=0,
            z=-10,
            apparent_magnitude=5.0,
        ),
        # On-axis in front, 50 pc away, brightest.
        CatalogObject(
            uid="B",
            source="t",
            object_type=ObjectType.STAR,
            x=0,
            y=0,
            z=-50,
            apparent_magnitude=1.0,
        ),
        # Behind the camera.
        CatalogObject(uid="C", source="t", object_type=ObjectType.STAR, x=0, y=0, z=10),
        # ~26.57 deg off axis, 11.18 pc away, a galaxy.
        CatalogObject(
            uid="D",
            source="t",
            object_type=ObjectType.GALAXY,
            x=5,
            y=0,
            z=-10,
            apparent_magnitude=8.0,
        ),
        # Beyond a 100 pc far plane.
        CatalogObject(uid="E", source="t", object_type=ObjectType.STAR, x=0, y=0, z=-200),
        # No Cartesian position -> never visible in 3D.
        CatalogObject(uid="F", source="t", object_type=ObjectType.STAR),
    ]


@pytest.fixture
def db() -> Database:
    database = Database(":memory:")
    import_objects(database, _objects(), dataset_name="t")
    yield database
    database.dispose()


def _state(**overrides) -> NavigatorState:
    base = dict(
        position=Vec3.of(0, 0, 0),
        direction=Vec3.of(0, 0, -1),
        up=Vec3.of(0, 1, 0),
        near_distance=0.0,
        far_distance=100.0,
        cone_angle_degrees=30.0,
        max_visible_objects=10,
    )
    base.update(overrides)
    return NavigatorState(**base)


def test_visible_sorted_by_distance(db: Database) -> None:
    assert [o.uid for o in visible_objects(db, _state())] == ["A", "D", "B"]


def test_visible_sorted_by_magnitude(db: Database) -> None:
    # B (mag 1) brightest, then A (5), then D (8).
    assert [o.uid for o in visible_objects(db, _state(), sort="magnitude")] == ["B", "A", "D"]


def test_cone_excludes_off_axis(db: Database) -> None:
    # 20 deg cone excludes D (~26.57 deg off axis).
    assert [o.uid for o in visible_objects(db, _state(cone_angle_degrees=20.0))] == ["A", "B"]


def test_far_distance_excludes(db: Database) -> None:
    # A 40 pc far plane drops B (50 pc).
    assert {o.uid for o in visible_objects(db, _state(far_distance=40.0))} == {"A", "D"}


def test_near_distance_excludes(db: Database) -> None:
    # A 20 pc near plane drops A and D (both < 20 pc); leaves B (50 pc).
    assert {o.uid for o in visible_objects(db, _state(near_distance=20.0))} == {"B"}


def test_max_visible_cap(db: Database) -> None:
    assert [o.uid for o in visible_objects(db, _state(max_visible_objects=2))] == ["A", "D"]


def test_type_filter(db: Database) -> None:
    visible = visible_objects(db, _state(), object_types={ObjectType.GALAXY})
    assert [o.uid for o in visible] == ["D"]


def test_magnitude_filter(db: Database) -> None:
    # Keep objects at least as bright as mag 5 -> A (5) and B (1); D (8) excluded.
    visible = visible_objects(db, _state(), max_magnitude=5.0)
    assert {o.uid for o in visible} == {"A", "B"}


def test_objects_without_cartesian_excluded(db: Database) -> None:
    uids = {o.uid for o in visible_objects(db, _state())}
    assert "F" not in uids  # no x/y/z
    assert "C" not in uids  # behind the camera
    assert "E" not in uids  # beyond the far plane


def test_unknown_sort_raises(db: Database) -> None:
    with pytest.raises(ValueError):
        visible_objects(db, _state(), sort="brightness")
