"""End-to-end MVP vertical slice.

Exercises the whole chain locally with no network and no Cinema 4D:

    sample catalog -> import into SQLite -> local API ->
    search -> inspect -> 2D sky payload -> visible-sector query.
"""

from fastapi.testclient import TestClient

from unav_core.data import write_sample_catalog
from unav_core.db import import_jsonl_to_db
from unav_server.app import create_app

_WIDE_STATE = {
    "position": {"x": 0, "y": 0, "z": 0},
    "direction": {"x": 0, "y": 0, "z": -1},
    "up": {"x": 0, "y": 1, "z": 0},
    "far_distance": 100000.0,
    "cone_angle_degrees": 180.0,
    "max_visible_objects": 1000,
}


def _build_database(tmp_path):
    sample = tmp_path / "sample.jsonl"
    written = write_sample_catalog(sample, 100, seed=42)
    assert written == 100  # step 1: sample catalog generation

    db_path = tmp_path / "unav.db"
    summary = import_jsonl_to_db(sample, db_path, "sample", enrich=True)
    assert summary.inserted == 100  # step 2: import into SQLite (enriched x/y/z)
    return db_path


def test_full_mvp_chain(tmp_path) -> None:
    db_path = _build_database(tmp_path)
    app = create_app(str(db_path), serve_ui=True)
    client = TestClient(app)
    try:
        # step 3: local API — health & datasets
        assert client.get("/health").json() == {"status": "ok", "object_count": 100}
        assert any(d["name"] == "sample" for d in client.get("/datasets").json())

        # step 4: the standalone UI is served (so a developer can open it)
        root = client.get("/")
        assert root.status_code == 200
        assert "UNAV" in root.text

        # step 5: search works against the local DB
        results = client.get("/objects/search", params={"q": "Sample Star", "limit": 200}).json()
        assert results["count"] == 50  # the 50 generated stars
        uid = results["objects"][0]["uid"]

        # step 6: object inspection works
        obj = client.get(f"/objects/{uid}").json()
        assert obj["uid"] == uid
        assert obj["ra_deg"] is not None and obj["dec_deg"] is not None
        assert client.get("/objects/does-not-exist").status_code == 404

        # step 7: 2D sky payload — every sample object has RA/Dec
        sky = client.post(
            "/sky/query-region",
            json={"ra_min": 0, "ra_max": 360, "dec_min": -90, "dec_max": 90, "limit": 1000},
        ).json()
        assert sky["count"] == 100
        assert all(o["ra_deg"] is not None and o["dec_deg"] is not None for o in sky["objects"])

        # step 8: visible-sector query returns enriched (3D) objects
        visible = client.post("/visible-sector/query", json={"state": _WIDE_STATE}).json()
        assert visible["count"] >= 50  # at least the enriched stars
        assert all(o["x"] is not None for o in visible["objects"])
    finally:
        app.state.service.dispose()
