"""Tests for the lightweight ``POST /visible-sector/query`` payload.

Covers the render-object shape (no per-point metadata), the result-cap flag, and
that full metadata loads lazily via ``GET /objects/{uid}`` on selection.
"""

from fastapi.testclient import TestClient

from unav_core.data import CatalogObject, ObjectType
from unav_core.db import import_objects
from unav_server.app import create_app

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

# Wide cone + far clip from the origin: sees all four cartesian seed objects.
_ALL_STATE = {
    "position": {"x": 0, "y": 0, "z": 0},
    "direction": {"x": 0, "y": 0, "z": -1},
    "up": {"x": 0, "y": 1, "z": 0},
    "far_distance": 1000.0,
    "cone_angle_degrees": 180.0,
    "max_visible_objects": 10,
}


def test_query_returns_lightweight_render_objects(client: TestClient) -> None:
    body = client.post("/visible-sector/query", json={"state": _ALL_STATE}).json()
    assert body["count"] == len(body["objects"]) == 4
    obj = body["objects"][0]
    assert set(obj) == _RENDER_FIELDS
    assert obj["display_color"].startswith("#")
    assert isinstance(obj["display_size"], (int, float))
    # Nothing heavy is shipped per point.
    for o in body["objects"]:
        assert "metadata" not in o
        assert "provenance" not in o
        assert "apparent_magnitude" not in o


def test_query_not_capped_when_under_limit(client: TestClient) -> None:
    body = client.post("/visible-sector/query", json={"state": _ALL_STATE}).json()
    assert body["capped"] is False
    assert body["max_visible_objects"] == 10
    assert body["count"] == 4


def test_query_capped_when_limit_reached(client: TestClient) -> None:
    state = {**_ALL_STATE, "max_visible_objects": 2}
    body = client.post("/visible-sector/query", json={"state": state}).json()
    assert body["count"] == 2
    assert body["capped"] is True
    assert body["max_visible_objects"] == 2


def test_metadata_loads_lazily_on_selection() -> None:
    app = create_app(":memory:")
    import_objects(
        app.state.service.db,
        [
            CatalogObject(
                uid="star-1",
                source="Gaia DR3",
                object_type=ObjectType.STAR,
                name="Metadata Star",
                ra_deg=10.0,
                dec_deg=20.0,
                distance_pc=12.0,
                x=1.0,
                y=2.0,
                z=3.0,
                apparent_magnitude=4.0,
                metadata={"phot_g_mean_mag": 4.2, "note": "rich record"},
            )
        ],
        dataset_name="seed",
    )
    with TestClient(app) as client:
        # 1) The bulk render payload carries NO metadata.
        body = client.post("/visible-sector/query", json={"state": _ALL_STATE}).json()
        point = next(o for o in body["objects"] if o["uid"] == "star-1")
        assert "metadata" not in point

        # 2) Selecting the object loads the full record (with metadata) on demand.
        full = client.get("/objects/star-1").json()
        assert full["metadata"] == {"phot_g_mean_mag": 4.2, "note": "rich record"}
        assert "provenance" in full
        assert full["apparent_magnitude"] == 4.0
