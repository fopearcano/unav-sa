"""Tests for navigator state, focus, visible-sector, routes and missions."""

from fastapi.testclient import TestClient

_STATE = {
    "position": {"x": 0, "y": 0, "z": 0},
    "direction": {"x": 0, "y": 0, "z": -1},
    "up": {"x": 0, "y": 1, "z": 0},
    "far_distance": 100.0,
    "cone_angle_degrees": 30.0,
    "max_visible_objects": 10,
}


def test_set_and_get_state(client: TestClient) -> None:
    assert client.post("/navigator/state", json=_STATE).status_code == 200
    state = client.get("/navigator/state").json()
    assert state["far_distance"] == 100.0
    assert state["position"] == {"x": 0.0, "y": 0.0, "z": 0.0}


def test_set_invalid_state_is_422(client: TestClient) -> None:
    bad = {**_STATE, "fov_degrees": 500.0}
    assert client.post("/navigator/state", json=bad).status_code == 422


def test_focus_moves_camera(client: TestClient) -> None:
    # gaia:1 is at (0, 0, -10); focusing from the origin at distance 5 -> (0, 0, -5).
    response = client.post("/navigator/focus/gaia:1", params={"distance": 5.0})
    assert response.status_code == 200
    assert response.json()["position"] == {"x": 0.0, "y": 0.0, "z": -5.0}


def test_focus_unknown_object_404(client: TestClient) -> None:
    assert client.post("/navigator/focus/missing").status_code == 404


def test_focus_without_position_400(client: TestClient) -> None:
    # 'nopos' has only sky coordinates (no x/y/z).
    assert client.post("/navigator/focus/nopos").status_code == 400


def test_visible_sector_with_explicit_state(client: TestClient) -> None:
    response = client.post("/visible-sector/query", json={"state": _STATE})
    assert response.status_code == 200
    uids = {o["uid"] for o in response.json()["objects"]}
    assert uids == {"gaia:1", "gaia:2"}


def test_visible_sector_uses_current_state(client: TestClient) -> None:
    client.post("/navigator/state", json=_STATE)
    response = client.post("/visible-sector/query", json={})
    assert {o["uid"] for o in response.json()["objects"]} == {"gaia:1", "gaia:2"}


def test_visible_sector_bad_sort_400(client: TestClient) -> None:
    response = client.post("/visible-sector/query", json={"state": _STATE, "sort": "bogus"})
    assert response.status_code == 400


def test_routes_create_and_list(client: TestClient) -> None:
    body = {
        "name": "tour",
        "waypoints": [{"kind": "coordinate", "position": {"x": 0, "y": 0, "z": 0}, "label": "a"}],
    }
    created = client.post("/routes", json=body)
    assert created.status_code == 200
    route_id = created.json()["route_id"]
    assert any(r["route_id"] == route_id for r in client.get("/routes").json())


def test_missions_create_and_list(client: TestClient) -> None:
    route = client.post(
        "/routes",
        json={
            "name": "m-route",
            "waypoints": [
                {"kind": "coordinate", "position": {"x": 0, "y": 0, "z": 0}, "label": "a"}
            ],
        },
    ).json()
    waypoint_id = route["waypoints"][0]["wid"]
    mission = {
        "title": "M",
        "route": route,
        "segments": [{"waypoint_id": waypoint_id, "hold_seconds": 1.0}],
    }
    created = client.post("/missions", json=mission)
    assert created.status_code == 200
    assert len(client.get("/missions").json()) >= 1
