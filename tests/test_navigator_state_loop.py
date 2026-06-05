"""Tests for the navigator state loop: state persistence, move, focus, query-current.

The backend holds the authoritative ``NavigatorState``; every mutation (set /
move / focus) persists, and the visible sector is queried *from* that state via
``POST /visible-sector/query-current``. See ``docs/NAVIGATOR_STATE_LOOP.md``.
"""

import math

from fastapi.testclient import TestClient

_RENDER_FIELDS = {
    "uid",
    "name",
    "source",
    "object_type",
    "x",
    "y",
    "z",
    "ra_deg",
    "dec_deg",
    "distance_pc",
    "display_color",
    "display_size",
}

_DEFAULT_STATE = {
    "position": {"x": 0, "y": 0, "z": 0},
    "direction": {"x": 0, "y": 0, "z": -1},
    "up": {"x": 0, "y": 1, "z": 0},
}

# Wide cone + far clip from the origin: sees all four cartesian seed objects.
_WIDE_STATE = {
    **_DEFAULT_STATE,
    "fov_degrees": 60.0,
    "near_distance": 0.0,
    "far_distance": 1000.0,
    "cone_angle_degrees": 180.0,
    "epoch": "J2016.0",
    "max_visible_objects": 10,
}


# --- state persistence / consistency ---


def test_state_get_post_roundtrip(client: TestClient) -> None:
    posted = client.post("/navigator/state", json=_WIDE_STATE).json()
    fetched = client.get("/navigator/state").json()
    assert fetched == posted  # UI and backend state stay consistent
    assert fetched["cone_angle_degrees"] == 180.0
    assert fetched["epoch"] == "J2016.0"
    assert fetched["max_visible_objects"] == 10


def test_full_state_fields_persist(client: TestClient) -> None:
    state = client.get("/navigator/state").json()
    # Every documented field is present and persisted.
    for field in (
        "position",
        "direction",
        "up",
        "fov_degrees",
        "near_distance",
        "far_distance",
        "cone_angle_degrees",
        "epoch",
        "max_visible_objects",
    ):
        assert field in state


# --- movement ---


def test_move_directions(client: TestClient) -> None:
    cases = {
        "forward": (0.0, 0.0, -10.0),
        "back": (0.0, 0.0, 10.0),
        "right": (10.0, 0.0, 0.0),
        "left": (-10.0, 0.0, 0.0),
        "up": (0.0, 10.0, 0.0),
        "down": (0.0, -10.0, 0.0),
    }
    for direction, expected in cases.items():
        client.post("/navigator/state", json=_DEFAULT_STATE)  # reset to origin
        state = client.post(
            "/navigator/move", json={"direction": direction, "distance": 10.0}
        ).json()
        pos = state["position"]
        assert (round(pos["x"], 6), round(pos["y"], 6), round(pos["z"], 6)) == expected


def test_move_persists_and_accumulates(client: TestClient) -> None:
    client.post("/navigator/state", json=_DEFAULT_STATE)
    client.post("/navigator/move", json={"direction": "forward", "distance": 5.0})
    moved = client.post("/navigator/move", json={"direction": "forward", "distance": 5.0}).json()
    assert moved["position"] == {"x": 0.0, "y": 0.0, "z": -10.0}
    # The move response and the persisted state agree.
    assert client.get("/navigator/state").json() == moved


def test_move_preserves_view_params(client: TestClient) -> None:
    client.post(
        "/navigator/state",
        json={
            **_DEFAULT_STATE,
            "fov_degrees": 50.0,
            "far_distance": 250.0,
            "cone_angle_degrees": 33.0,
            "max_visible_objects": 7,
        },
    )
    state = client.post("/navigator/move", json={"direction": "up", "distance": 3.0}).json()
    assert state["fov_degrees"] == 50.0
    assert state["far_distance"] == 250.0
    assert state["cone_angle_degrees"] == 33.0
    assert state["max_visible_objects"] == 7
    assert state["position"]["y"] == 3.0


def test_move_default_distance(client: TestClient) -> None:
    client.post("/navigator/state", json=_DEFAULT_STATE)
    state = client.post("/navigator/move", json={"direction": "forward"}).json()
    assert state["position"]["z"] == -10.0  # default distance is 10 pc


def test_move_rejects_unknown_direction(client: TestClient) -> None:
    assert client.post("/navigator/move", json={"direction": "sideways"}).status_code == 422


def test_move_rejects_nonpositive_distance(client: TestClient) -> None:
    assert (
        client.post("/navigator/move", json={"direction": "forward", "distance": 0.0}).status_code
        == 422
    )
    assert (
        client.post("/navigator/move", json={"direction": "forward", "distance": -5.0}).status_code
        == 422
    )


# --- focus ---


def test_focus_persists_state(client: TestClient) -> None:
    # gaia:1 is at (0,0,-10); focus from origin at distance 5 -> (0,0,-5).
    moved = client.post("/navigator/focus/gaia:1", params={"distance": 5.0}).json()
    assert moved["position"] == {"x": 0.0, "y": 0.0, "z": -5.0}
    # The focus persisted to the server's state.
    assert client.get("/navigator/state").json()["position"] == {"x": 0.0, "y": 0.0, "z": -5.0}


def test_focus_aims_direction_at_object(client: TestClient) -> None:
    state = client.post("/navigator/focus/gaia:2").json()  # gaia:2 at (5,0,-10)
    d = state["direction"]
    norm = math.sqrt(5**2 + 10**2)
    assert round(d["x"], 6) == round(5 / norm, 6)
    assert round(d["y"], 6) == 0.0
    assert round(d["z"], 6) == round(-10 / norm, 6)


# --- query-current (refresh from persisted state) ---


def test_query_current_reflects_default_state(client: TestClient) -> None:
    # The default state (cone 45, dir -z) sees only the two -z objects.
    body = client.post("/visible-sector/query-current").json()
    assert {o["uid"] for o in body["objects"]} == {"gaia:1", "gaia:2"}


def test_query_current_uses_persisted_state(client: TestClient) -> None:
    client.post("/navigator/state", json={**_WIDE_STATE, "max_visible_objects": 100})
    body = client.post("/visible-sector/query-current").json()
    assert body["count"] == 4
    assert {o["uid"] for o in body["objects"]} == {"gaia:1", "gaia:2", "m87", "3c273"}
    # Lightweight render objects only — no per-point metadata.
    assert set(body["objects"][0]) == _RENDER_FIELDS
    for o in body["objects"]:
        assert "metadata" not in o and "provenance" not in o


def test_query_current_obeys_cap(client: TestClient) -> None:
    client.post("/navigator/state", json={**_WIDE_STATE, "max_visible_objects": 2})
    body = client.post("/visible-sector/query-current").json()
    assert body["count"] == 2
    assert body["capped"] is True
    assert body["max_visible_objects"] == 2


def test_facing_plus_z_then_query_current_sees_only_front(client: TestClient) -> None:
    # Aim a narrow cone toward +z; only the +z objects are in view.
    client.post(
        "/navigator/state",
        json={**_WIDE_STATE, "cone_angle_degrees": 45.0, "direction": {"x": 0, "y": 0, "z": 1}},
    )
    body = client.post("/visible-sector/query-current").json()
    assert {o["uid"] for o in body["objects"]} == {"m87", "3c273"}  # the +z objects
