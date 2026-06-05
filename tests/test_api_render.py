"""Tests for the lightweight 3D render payload endpoints."""

from fastapi.testclient import TestClient

_STATE = {
    "position": {"x": 0, "y": 0, "z": 0},
    "direction": {"x": 0, "y": 0, "z": -1},
    "up": {"x": 0, "y": 1, "z": 0},
    "far_distance": 100.0,
    "cone_angle_degrees": 30.0,
}

_POINT_FIELDS = {"uid", "source", "object_type", "x", "y", "z", "color", "size", "name"}


def test_current_render_payload_shape(client: TestClient) -> None:
    body = client.get("/visible-sector/current/render").json()
    assert body["count"] == len(body["points"])
    # Default navigator state (origin, -z) sees the two front cartesian objects.
    assert {p["uid"] for p in body["points"]} == {"gaia:1", "gaia:2"}
    point = body["points"][0]
    assert set(point) == _POINT_FIELDS
    assert point["color"].startswith("#")
    assert isinstance(point["size"], (int, float))


def test_render_payload_is_slim(client: TestClient) -> None:
    point = client.get("/visible-sector/current/render").json()["points"][0]
    assert "metadata" not in point
    assert "provenance" not in point
    assert "redshift" not in point
    assert "apparent_magnitude" not in point


def test_render_color_by_type(client: TestClient) -> None:
    points = {p["uid"]: p for p in client.get("/visible-sector/current/render").json()["points"]}
    assert points["gaia:1"]["object_type"] == "star"
    assert points["gaia:1"]["color"] == "#cfe8ff"  # the star colour


def test_render_with_explicit_state(client: TestClient) -> None:
    body = client.post("/visible-sector/render", json={"state": _STATE}).json()
    assert {p["uid"] for p in body["points"]} == {"gaia:1", "gaia:2"}


def test_render_bad_sort_400(client: TestClient) -> None:
    response = client.post("/visible-sector/render", json={"sort": "bogus"})
    assert response.status_code == 400
