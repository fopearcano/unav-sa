"""Tests for the 2D sky endpoints: RA/Dec region query and current visible sector."""

from fastapi.testclient import TestClient

_VIEW_STATE = {
    "position": {"x": 0, "y": 0, "z": 0},
    "direction": {"x": 0, "y": 0, "z": -1},
    "up": {"x": 0, "y": 1, "z": 0},
    "far_distance": 100.0,
    "cone_angle_degrees": 30.0,
}


def test_sky_region_returns_radec_payload(client: TestClient) -> None:
    response = client.post(
        "/sky/query-region",
        json={"ra_min": 0, "ra_max": 360, "dec_min": -90, "dec_max": 90},
    )
    assert response.status_code == 200
    objects = response.json()["objects"]
    # Seed objects with RA/Dec: gaia:1 (279.2, 38.8) and nopos (1.0, 2.0).
    assert {o["uid"] for o in objects} == {"gaia:1", "nopos"}
    assert all(o["ra_deg"] is not None and o["dec_deg"] is not None for o in objects)


def test_sky_region_box(client: TestClient) -> None:
    response = client.post(
        "/sky/query-region",
        json={"ra_min": 270, "ra_max": 285, "dec_min": 30, "dec_max": 45},
    )
    assert {o["uid"] for o in response.json()["objects"]} == {"gaia:1"}


def test_sky_region_wraps_across_seam(client: TestClient) -> None:
    # ra_min > ra_max wraps across 0/360; nopos is at RA 1.0.
    response = client.post(
        "/sky/query-region",
        json={"ra_min": 350, "ra_max": 5, "dec_min": -5, "dec_max": 5},
    )
    assert {o["uid"] for o in response.json()["objects"]} == {"nopos"}


def test_sky_region_invalid_dec_order_422(client: TestClient) -> None:
    response = client.post(
        "/sky/query-region",
        json={"ra_min": 0, "ra_max": 10, "dec_min": 50, "dec_max": 10},
    )
    assert response.status_code == 422


def test_sky_region_out_of_range_422(client: TestClient) -> None:
    response = client.post(
        "/sky/query-region",
        json={"ra_min": 0, "ra_max": 400, "dec_min": -90, "dec_max": 90},
    )
    assert response.status_code == 422


def test_visible_sector_current(client: TestClient) -> None:
    client.post("/navigator/state", json=_VIEW_STATE)
    response = client.get("/visible-sector/current")
    assert response.status_code == 200
    assert {o["uid"] for o in response.json()["objects"]} == {"gaia:1", "gaia:2"}
