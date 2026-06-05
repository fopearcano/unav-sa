"""Tests for waypoints, routes and route analytics."""

import pytest
from pydantic import ValidationError

from unav_core.data import CatalogObject, ObjectType
from unav_core.navigation import Bookmark, Vec3
from unav_core.routes import Route, Waypoint, WaypointKind


def _star(uid: str, x: float, y: float, z: float, name: str = "star") -> CatalogObject:
    return CatalogObject(
        uid=uid, source="Gaia DR3", object_type=ObjectType.STAR, name=name, x=x, y=y, z=z
    )


# --- waypoints ---


def test_waypoint_from_object_caches_fields() -> None:
    wp = Waypoint.from_object(_star("gaia:1", 1.0, 2.0, 3.0, name="Vega"))
    assert wp.kind is WaypointKind.CATALOG_OBJECT
    assert wp.object_uid == "gaia:1"
    assert wp.label == "Vega"
    assert wp.object_type is ObjectType.STAR
    assert wp.source == "Gaia DR3"
    assert wp.position == Vec3.of(1.0, 2.0, 3.0)


def test_waypoint_from_coordinate_and_annotation() -> None:
    coord = Waypoint.from_coordinate(Vec3.of(0, 0, 10), label="mid")
    assert coord.kind is WaypointKind.COORDINATE and coord.has_position
    note = Waypoint.annotation_waypoint("scenic", label="note")
    assert note.kind is WaypointKind.ANNOTATION_ONLY and not note.has_position


def test_waypoint_from_bookmark() -> None:
    bm = Bookmark.for_coordinate(Vec3.of(5, 0, 0), label="field")
    wp = Waypoint.from_bookmark(bm)
    assert wp.kind is WaypointKind.BOOKMARK
    assert wp.bookmark_id == bm.bookmark_id
    assert wp.position == Vec3.of(5, 0, 0)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"kind": WaypointKind.CATALOG_OBJECT},  # missing object_uid
        {"kind": WaypointKind.COORDINATE},  # missing position
        {"kind": WaypointKind.BOOKMARK},  # missing bookmark_id
        {"kind": WaypointKind.ANNOTATION_ONLY},  # missing annotation/label
    ],
)
def test_waypoint_kind_validation(kwargs) -> None:
    with pytest.raises(ValidationError):
        Waypoint(**kwargs)


# --- route editing ---


def test_route_add_and_len() -> None:
    route = Route(name="r")
    route.add_waypoint(Waypoint.from_coordinate(Vec3.of(0, 0, 0), label="a"))
    route.add_waypoint(Waypoint.from_coordinate(Vec3.of(1, 0, 0), label="b"))
    assert len(route) == 2


def test_route_insert_remove_move() -> None:
    route = Route(name="r")
    a = route.add_waypoint(Waypoint.from_coordinate(Vec3.of(0, 0, 0), label="a"))
    b = route.add_waypoint(Waypoint.from_coordinate(Vec3.of(1, 0, 0), label="b"))
    c = Waypoint.from_coordinate(Vec3.of(2, 0, 0), label="c")
    route.add_waypoint(c, index=0)  # insert at front
    assert [w.label for w in route.waypoints] == ["c", "a", "b"]

    route.move_waypoint(b.wid, 0)
    assert route.waypoints[0].wid == b.wid

    removed = route.remove_waypoint(a.wid)
    assert removed.wid == a.wid
    assert len(route) == 2
    with pytest.raises(KeyError):
        route.remove_waypoint("does-not-exist")


def test_route_reorder() -> None:
    route = Route(name="r")
    ids = [route.add_waypoint(Waypoint.from_coordinate(Vec3.of(i, 0, 0))).wid for i in range(3)]
    route.reorder(list(reversed(ids)))
    assert [w.wid for w in route.waypoints] == list(reversed(ids))
    with pytest.raises(ValueError):
        route.reorder(ids[:2])  # not a permutation


# --- analytics ---


def test_distance_summary_skips_unpositioned() -> None:
    route = Route(name="r")
    route.add_waypoint(Waypoint.from_coordinate(Vec3.of(0, 0, 0)))
    route.add_waypoint(Waypoint.annotation_waypoint("note", label="n"))  # no position
    route.add_waypoint(Waypoint.from_coordinate(Vec3.of(3, 4, 0)))  # 5 from origin
    route.add_waypoint(Waypoint.from_coordinate(Vec3.of(3, 4, 0)))  # 0 from previous
    summary = route.distance_summary()
    assert summary.positioned_waypoints == 3
    assert summary.leg_count == 2
    assert summary.total_distance_pc == pytest.approx(5.0)
    assert summary.leg_distances_pc == pytest.approx([5.0, 0.0])


def test_source_and_type_summaries() -> None:
    route = Route(name="r")
    route.add_waypoint(Waypoint.from_object(_star("gaia:1", 0, 0, 0)))
    route.add_waypoint(Waypoint.from_object(_star("gaia:2", 1, 0, 0)))
    route.add_waypoint(
        Waypoint.from_object(
            CatalogObject(uid="ned:1", source="NED", object_type=ObjectType.GALAXY, x=2, y=0, z=0)
        )
    )
    route.add_waypoint(Waypoint.from_coordinate(Vec3.of(9, 0, 0)))  # no source/type
    assert route.source_summary() == {"Gaia DR3": 2, "NED": 1}
    assert route.object_type_summary() == {"star": 2, "galaxy": 1}


def test_route_json_roundtrip() -> None:
    route = Route(name="tour", description="demo")
    route.add_waypoint(Waypoint.from_object(_star("gaia:1", 1, 2, 3, name="Vega")))
    route.add_waypoint(Waypoint.from_coordinate(Vec3.of(0, 0, 10), label="mid"))
    route.add_waypoint(Waypoint.annotation_waypoint("here", label="note"))
    assert Route.from_json(route.to_json()) == route
