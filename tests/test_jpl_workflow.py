"""End-to-end JPL Horizons solar-system workflow with MOCKED astroquery (no network).

fetch (mocked, classified by name) -> write JSONL -> import (enriched) -> search
planets + view in 3D + inspect the epoch/center. Also exercises the
``tools/fetch_jpl_solar_system.py`` CLI with ``--db``. See
``docs/JPL_SOLAR_SYSTEM_WORKFLOW.md``.
"""

import importlib.util
import sys
import types
from pathlib import Path

from astropy.table import Table
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from unav_core.connectors.jpl import fetch_jpl_solar_system
from unav_core.data import ObjectType
from unav_core.data.io import write_jsonl
from unav_core.db import import_jsonl_to_db
from unav_server.app import create_app

_REPO_ROOT = Path(__file__).resolve().parent.parent
_EPOCH = "2026-01-01T00:00:00"

# Distinct per-body sky positions so the bodies spread out in 3D.
_POSITIONS = {
    "Mercury": (10.0, 1.0, 0.4, "Mercury (199)"),
    "Venus": (20.0, 2.0, 0.7, "Venus (299)"),
    "Earth": (30.0, 3.0, 1.0, "Earth (399)"),
    "Mars": (40.0, 4.0, 1.5, "Mars (499)"),
    "Moon": (41.0, 4.1, 0.0026, "Moon (301)"),
}


def _install_fake_horizons(monkeypatch) -> None:
    class FakeHorizons:
        def __init__(self, id=None, location=None, epochs=None) -> None:
            self.id = id

        def ephemerides(self, *args, **kwargs) -> Table:
            ra, dec, delta, name = _POSITIONS.get(self.id, (10.0, 0.0, 1.0, str(self.id)))
            table = Table()
            table["targetname"] = [name]
            table["RA"] = [ra]
            table["DEC"] = [dec]
            table["delta"] = [delta]
            table["V"] = [0.0]
            return table

    fake = types.ModuleType("astroquery.jplhorizons")
    fake.Horizons = FakeHorizons
    monkeypatch.setitem(sys.modules, "astroquery", types.ModuleType("astroquery"))
    monkeypatch.setitem(sys.modules, "astroquery.jplhorizons", fake)


def test_jpl_workflow_import_search_3d_inspect(monkeypatch, tmp_path) -> None:
    _install_fake_horizons(monkeypatch)
    bodies = ["Mercury", "Venus", "Earth", "Mars", "Moon"]
    objects = fetch_jpl_solar_system(bodies, _EPOCH)
    assert len(objects) == 5

    # Names are classified (planets/moon) -> distinct type colouring downstream.
    by_body = {o.metadata["body"]: o.object_type for o in objects}
    assert by_body["Mars"] is ObjectType.PLANET
    assert by_body["Moon"] is ObjectType.MOON

    jsonl = tmp_path / "jpl_solar_system.jsonl"
    write_jsonl(objects, jsonl)
    db_path = tmp_path / "unav.db"
    summary = import_jsonl_to_db(jsonl, db_path, "jpl_solar_system_2026", enrich=True)
    assert summary.inserted == 5

    app = create_app(str(db_path))
    with TestClient(app) as client:
        # dataset list shows the JPL dataset
        datasets = client.get("/datasets").json()
        assert any(
            d["name"] == "jpl_solar_system_2026" and d["source"] == "JPL Horizons" for d in datasets
        )

        # planets are searchable (4 planets; the Moon is not a planet)
        planets = client.get("/objects/search", params={"object_type": "planet"}).json()
        assert planets["count"] == 4
        assert all(o["object_type"] == "planet" for o in planets["objects"])

        # all five bodies appear in 3D (have x/y/z) via a wide visible-sector query
        visible = client.post(
            "/visible-sector/query",
            json={
                "state": {
                    "position": {"x": 0, "y": 0, "z": 0},
                    "direction": {"x": 0, "y": 0, "z": -1},
                    "up": {"x": 0, "y": 1, "z": 0},
                    "far_distance": 1000.0,
                    "cone_angle_degrees": 180.0,
                    "max_visible_objects": 100,
                }
            },
        ).json()
        assert visible["count"] == 5

        # inspect Mars: epoch + center are visible (metadata + provenance)
        obj = client.get("/objects/jpl:Mars:2026-01-01T00:00:00").json()
        assert obj["object_type"] == "planet"
        assert obj["x"] is not None and obj["y"] is not None and obj["z"] is not None
        assert obj["metadata"]["epoch"] == _EPOCH
        assert obj["metadata"]["center"] == "@sun"
        assert obj["provenance"]["epoch"] == _EPOCH


def _load_tool(name: str):
    spec = importlib.util.spec_from_file_location(name, _REPO_ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_solar_system_with_db(monkeypatch, tmp_path) -> None:
    _install_fake_horizons(monkeypatch)
    tool = _load_tool("fetch_jpl_solar_system")
    jsonl = tmp_path / "jpl_solar_system.jsonl"
    db_path = tmp_path / "unav.db"

    result = CliRunner().invoke(
        tool.app,
        [
            "--epoch",
            _EPOCH,
            "--bodies",
            "Mercury,Venus,Earth,Mars,Moon",
            "--output",
            str(jsonl),
            "--db",
            str(db_path),
            "--dataset-name",
            "jpl_solar_system_2026",
        ],
    )
    assert result.exit_code == 0, result.output
    assert jsonl.exists()

    app = create_app(str(db_path))
    with TestClient(app) as client:
        assert client.get("/health").json()["object_count"] == 5
        assert client.get("/objects/search", params={"object_type": "planet"}).json()["count"] == 4
