"""Tests for missions and deterministic playback."""

import pytest
from pydantic import ValidationError

from unav_core.missions import (
    Mission,
    MissionSegment,
    evaluate_at_progress,
    evaluate_at_seconds,
)
from unav_core.navigation import NavigatorState, Vec3
from unav_core.routes import Route, Waypoint


def _two_stop_route() -> Route:
    route = Route(name="two-stop")
    route.add_waypoint(Waypoint.from_coordinate(Vec3.of(0, 0, 0), label="A"))
    route.add_waypoint(Waypoint.from_coordinate(Vec3.of(10, 0, 0), label="B"))
    return route


def _cameras(route: Route) -> dict[str, NavigatorState]:
    a, b = route.waypoints
    return {
        a.wid: NavigatorState(position=Vec3.of(0, 0, 0), direction=Vec3.of(0, 0, -1)),
        b.wid: NavigatorState(position=Vec3.of(10, 0, 0), direction=Vec3.of(0, 0, -1)),
    }


def _mission(transition: float = 10.0, hold: float = 0.0) -> Mission:
    route = _two_stop_route()
    return Mission.build(
        route,
        title="A to B",
        cameras=_cameras(route),
        transition_seconds=transition,
        hold_seconds=hold,
    )


def test_build_creates_segments_per_waypoint() -> None:
    mission = _mission()
    assert len(mission.segments) == 2
    assert mission.segments[0].transition_seconds == 0.0  # first ignored
    assert mission.segments[1].transition_seconds == 10.0
    assert all(seg.camera is not None for seg in mission.segments)


def test_total_duration_excludes_first_transition() -> None:
    mission = _mission(transition=10.0, hold=2.0)
    # holds: 2 + 2 = 4; transitions (after first): 10  -> 14
    assert mission.total_duration_seconds == pytest.approx(14.0)


def test_segment_must_reference_route() -> None:
    route = _two_stop_route()
    with pytest.raises(ValidationError):
        Mission(title="bad", route=route, segments=[MissionSegment(waypoint_id="nope")])


def test_playback_endpoints_and_midpoint() -> None:
    mission = _mission(transition=10.0, hold=0.0)
    start = evaluate_at_progress(mission, 0.0)
    mid = evaluate_at_progress(mission, 0.5)
    end = evaluate_at_progress(mission, 1.0)
    assert start.camera.position == Vec3.of(0, 0, 0)
    assert start.phase == "start"
    assert mid.camera.position == Vec3.of(5, 0, 0)
    assert mid.phase == "transition"
    assert end.camera.position == Vec3.of(10, 0, 0)


def test_playback_at_seconds_matches_progress() -> None:
    mission = _mission(transition=10.0)
    assert evaluate_at_seconds(mission, 5.0).camera.position == Vec3.of(5, 0, 0)


def test_playback_clamps_out_of_range() -> None:
    mission = _mission(transition=10.0)
    assert evaluate_at_progress(mission, -1.0).camera.position == Vec3.of(0, 0, 0)
    assert evaluate_at_progress(mission, 2.0).camera.position == Vec3.of(10, 0, 0)


def test_playback_is_deterministic() -> None:
    mission = _mission(transition=10.0)
    assert evaluate_at_progress(mission, 0.3) == evaluate_at_progress(mission, 0.3)


def test_playback_hold_phase() -> None:
    mission = _mission(transition=4.0, hold=2.0)
    # timeline: hold A [0,2], transition A->B [2,6], hold B [6,8]
    assert evaluate_at_seconds(mission, 1.0).phase == "hold"
    assert evaluate_at_seconds(mission, 1.0).camera.position == Vec3.of(0, 0, 0)
    assert evaluate_at_seconds(mission, 4.0).phase == "transition"
    # transition runs [2, 6]; t=4 is the midpoint -> (5, 0, 0)
    assert evaluate_at_seconds(mission, 4.0).camera.position == Vec3.of(5, 0, 0)
    assert evaluate_at_seconds(mission, 7.0).phase == "hold"
    assert evaluate_at_seconds(mission, 7.0).camera.position == Vec3.of(10, 0, 0)


def test_playback_requires_cameras() -> None:
    route = _two_stop_route()
    mission = Mission.build(route, title="no cams")  # cameras=None
    assert not mission.has_cameras()
    with pytest.raises(ValueError):
        evaluate_at_progress(mission, 0.5)


def test_mission_json_roundtrip() -> None:
    mission = _mission(transition=10.0, hold=1.0)
    assert Mission.from_json(mission.to_json()) == mission
