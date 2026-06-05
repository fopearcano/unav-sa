"""End-to-end Gaia regional-import workflow with MOCKED astroquery (no network).

fetch (mocked) -> normalise -> write JSONL -> import into the DB (enriched) ->
search + inspect via the API, with Gaia fields and provenance visible. Also
exercises the ``tools/fetch_gaia_region.py`` CLI (including ``--db`` import).
See ``docs/GAIA_WORKFLOW.md``.
"""

import importlib.util
import sys
import types
from pathlib import Path

import numpy as np
from astropy.table import Table
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from unav_core.connectors.gaia import fetch_gaia_region
from unav_core.data.io import write_jsonl
from unav_core.db import import_jsonl_to_db
from unav_server.app import create_app

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _install_fake_gaia(monkeypatch, table: Table) -> None:
    class FakeJob:
        def get_results(self) -> Table:
            return table

    class FakeGaia:
        @staticmethod
        def launch_job(adql: str, *args, **kwargs) -> FakeJob:
            return FakeJob()

    fake = types.ModuleType("astroquery.gaia")
    fake.Gaia = FakeGaia
    monkeypatch.setitem(sys.modules, "astroquery", types.ModuleType("astroquery"))
    monkeypatch.setitem(sys.modules, "astroquery.gaia", fake)


def _gaia_table() -> Table:
    table = Table()
    table["source_id"] = np.array([4295806720, 34361129088], dtype="int64")
    table["ra"] = [56.70, 56.80]
    table["dec"] = [24.10, 24.15]
    table["parallax"] = [5.0, 2.0]  # -> 200 pc, 500 pc
    table["phot_g_mean_mag"] = [9.5, 12.1]
    table["bp_rp"] = [0.7, 1.2]
    table["pmra"] = [1.0, -0.5]
    table["pmdec"] = [-2.0, 0.6]
    table["radial_velocity"] = [10.0, -3.0]
    return table


def test_gaia_workflow_fetch_import_inspect(monkeypatch, tmp_path) -> None:
    _install_fake_gaia(monkeypatch, _gaia_table())

    # fetch (mocked) + normalise
    objects = fetch_gaia_region(56.75, 24.12, 0.2, limit=500)
    assert len(objects) == 2
    jsonl = tmp_path / "gaia_test.jsonl"
    write_jsonl(objects, jsonl)

    # import into the DB (enriched -> x/y/z for 3D)
    db_path = tmp_path / "unav.db"
    summary = import_jsonl_to_db(jsonl, db_path, "gaia_test", enrich=True)
    assert summary.inserted == 2

    app = create_app(str(db_path))
    with TestClient(app) as client:
        # dataset list shows the Gaia dataset
        datasets = client.get("/datasets").json()
        assert any(d["name"] == "gaia_test" and d["source"] == "Gaia DR3" for d in datasets)

        # searchable (by source)
        found = client.get("/objects/search", params={"source": "Gaia DR3", "limit": 10}).json()
        assert found["count"] == 2

        # inspect: Gaia fields + 3D position + provenance all present
        obj = client.get("/objects/gaia:4295806720").json()
        assert obj["color_index"] == 0.7
        assert obj["proper_motion_ra_masyr"] == 1.0
        assert obj["radial_velocity_kms"] == 10.0
        assert obj["distance_pc"] == 200.0  # 1000 / parallax(5)
        assert obj["ra_deg"] is not None and obj["dec_deg"] is not None  # viewable in 2D
        assert obj["x"] is not None and obj["y"] is not None and obj["z"] is not None  # 3D
        prov = obj["provenance"]
        assert prov is not None
        assert prov["source"] == "Gaia DR3"
        assert prov["epoch"] == "J2016.0"
        assert prov["retrieved_at"] is not None


def _load_tool():
    spec = importlib.util.spec_from_file_location(
        "fetch_gaia_region_tool", _REPO_ROOT / "tools" / "fetch_gaia_region.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_fetch_and_direct_import(monkeypatch, tmp_path) -> None:
    _install_fake_gaia(monkeypatch, _gaia_table())
    tool = _load_tool()
    jsonl = tmp_path / "gaia_test.jsonl"
    db_path = tmp_path / "unav.db"

    result = CliRunner().invoke(
        tool.app,
        [
            "--ra",
            "56.75",
            "--dec",
            "24.12",
            "--radius-deg",
            "0.2",
            "--limit",
            "500",
            "--output",
            str(jsonl),
            "--db",
            str(db_path),
            "--dataset-name",
            "gaia_test",
        ],
    )
    assert result.exit_code == 0, result.output
    assert jsonl.exists()

    app = create_app(str(db_path))
    with TestClient(app) as client:
        assert client.get("/health").json()["object_count"] == 2
        assert any(d["name"] == "gaia_test" for d in client.get("/datasets").json())
