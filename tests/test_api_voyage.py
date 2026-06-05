"""Tests for the voyage-planning API: bookmarks, routes, missions + persistence."""

import pytest
from fastapi.testclient import TestClient

from unav_server.app import create_app

# --- bookmarks ---


def test_bookmark_crud_and_cached_position(client: TestClient) -> None:
    # Bookmark by uid only -> the server caches the object's position from the DB.
    created = client.post("/bookmarks", json={"label": "Vega", "object_uid": "gaia:1"}).json()
    assert created["object_uid"] == "gaia:1"
    assert created["position"] == {"x": 0.0, "y": 0.0, "z": -10.0}  # gaia:1's position
    bid = created["bookmark_id"]

    assert any(b["bookmark_id"] == bid for b in client.get("/bookmarks").json())
    assert client.delete(f"/bookmarks/{bid}").status_code == 204
    assert all(b["bookmark_id"] != bid for b in client.get("/bookmarks").json())
    assert client.delete(f"/bookmarks/{bid}").status_code == 404  # already gone


def test_coordinate_bookmark(client: TestClient) -> None:
    b = client.post("/bookmarks", json={"label": "home", "position": {"x": 1, "y": 2, "z": 3}})
    assert b.status_code == 200
    assert b.json()["position"] == {"x": 1.0, "y": 2.0, "z": 3.0}


# --- routes ---


def test_route_build_add_object_and_summary(client: TestClient) -> None:
    route = client.post("/routes", json={"name": "grand tour"}).json()
    rid = route["route_id"]
    assert route["waypoints"] == []

    client.post(f"/routes/{rid}/add-object/gaia:1")  # (0, 0, -10)
    route = client.post(f"/routes/{rid}/add-object/gaia:2").json()  # (5, 0, -10)
    assert [w["object_uid"] for w in route["waypoints"]] == ["gaia:1", "gaia:2"]
    assert route["waypoints"][0]["position"] == {"x": 0.0, "y": 0.0, "z": -10.0}

    # gaia:1 -> gaia:2 is exactly 5 pc.
    summary = client.get(f"/routes/{rid}/summary").json()
    assert summary["leg_count"] == 1
    assert summary["positioned_waypoints"] == 2
    assert summary["total_distance_pc"] == pytest.approx(5.0, abs=1e-9)


def test_route_add_object_unknown_404(client: TestClient) -> None:
    rid = client.post("/routes", json={"name": "t"}).json()["route_id"]
    assert client.post(f"/routes/{rid}/add-object/nope").status_code == 404
    assert client.post("/routes/nope/add-object/gaia:1").status_code == 404


def test_route_update_reorder_and_delete(client: TestClient) -> None:
    rid = client.post("/routes", json={"name": "t"}).json()["route_id"]
    client.post(f"/routes/{rid}/add-object/gaia:1")
    route = client.post(f"/routes/{rid}/add-object/gaia:2").json()

    # reorder (reverse) and rename via PUT
    route["name"] = "reordered"
    route["waypoints"] = list(reversed(route["waypoints"]))
    updated = client.put(f"/routes/{rid}", json=route).json()
    assert updated["route_id"] == rid
    assert updated["name"] == "reordered"
    assert [w["object_uid"] for w in updated["waypoints"]] == ["gaia:2", "gaia:1"]

    assert client.delete(f"/routes/{rid}").status_code == 204
    assert client.get(f"/routes/{rid}").status_code == 404


# --- missions ---


def test_mission_create_from_route_and_add_route(client: TestClient) -> None:
    rid = client.post("/routes", json={"name": "r1"}).json()["route_id"]
    route = client.post(f"/routes/{rid}/add-object/gaia:1").json()
    wid = route["waypoints"][0]["wid"]

    mission = client.post(
        "/missions",
        json={"title": "Voyage", "route": route, "segments": [{"waypoint_id": wid}]},
    ).json()
    mid = mission["mission_id"]
    assert mission["title"] == "Voyage"
    assert any(m["mission_id"] == mid for m in client.get("/missions").json())

    # add a second route's waypoints into the mission
    rid2 = client.post("/routes", json={"name": "r2"}).json()["route_id"]
    client.post(f"/routes/{rid2}/add-object/gaia:2")
    merged = client.post(f"/missions/{mid}/add-route/{rid2}").json()
    assert [w["object_uid"] for w in merged["route"]["waypoints"]] == ["gaia:1", "gaia:2"]
    assert len(merged["segments"]) == 2

    assert client.delete(f"/missions/{mid}").status_code == 204
    assert client.get(f"/missions/{mid}").status_code == 404


def test_mission_add_route_unknown_404(client: TestClient) -> None:
    assert client.post("/missions/nope/add-route/also-nope").status_code == 404


# --- persistence across restart ---


def test_voyage_persists_across_restart(tmp_path) -> None:
    db = str(tmp_path / "unav.db")

    # Session 1: create a route, a bookmark and a mission.
    app1 = create_app(db)
    with TestClient(app1) as c1:
        route = c1.post("/routes", json={"name": "persisted route"}).json()
        rid = route["route_id"]
        c1.post("/bookmarks", json={"label": "home", "position": {"x": 1, "y": 2, "z": 3}})
        mission = c1.post("/missions", json={"title": "voyage", "route": route}).json()
        mid = mission["mission_id"]

    # Session 2: a fresh app over the same DB file == an app restart.
    app2 = create_app(db)
    with TestClient(app2) as c2:
        assert any(r["route_id"] == rid for r in c2.get("/routes").json())
        assert any(m["mission_id"] == mid for m in c2.get("/missions").json())
        assert len(c2.get("/bookmarks").json()) == 1
