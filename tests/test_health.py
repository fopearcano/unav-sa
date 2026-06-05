"""Tests for the local health check."""

from pathlib import Path

from unav_core.config import load_config
from unav_core.health import health_report, render_health


def test_report_structure_and_core_ok(tmp_path) -> None:
    cfg = load_config(
        env={
            "UNAV_DATA_DIR": str(tmp_path / "data"),
            "UNAV_SAMPLES_DIR": str(tmp_path / "samples"),
        },
        root=tmp_path,
    )
    report = health_report(cfg)
    assert {
        "python",
        "core_ok",
        "packages",
        "optional",
        "config",
        "sample_data",
        "database",
        "server",
    } <= report.keys()
    # The core stack is installed in the test environment.
    assert report["core_ok"] is True
    # A fresh tmp dir has no sample data and no database.
    assert report["sample_data"]["exists"] is False
    assert report["database"]["exists"] is False
    assert report["database"]["object_count"] is None
    assert report["server"]["status"] == "not checked"


def test_render_explains_missing_optional_packages() -> None:
    report = health_report(load_config(env={}))
    text = render_health(report)
    assert "optional packages" in text
    # astroquery is optional; if absent, the rendering must say so + how to get it.
    if report["packages"]["astroquery"] is None:
        assert "astroquery" in text
        assert "not installed" in text
        assert "[query]" in text


def test_database_object_count_when_present(tmp_path) -> None:
    # Build a tiny DB and point the config at it.
    from unav_core.data import CatalogObject, ObjectType
    from unav_core.db import Database, import_objects

    db_path = tmp_path / "unav.db"
    db = Database(db_path)
    import_objects(
        db, [CatalogObject(uid="x", source="s", object_type=ObjectType.STAR)], dataset_name="d"
    )
    db.dispose()

    cfg = load_config(env={"UNAV_DB_PATH": str(db_path)}, root=tmp_path)
    report = health_report(cfg)
    assert report["database"]["exists"] is True
    assert report["database"]["object_count"] == 1


def test_server_probe_unreachable() -> None:
    # Nothing should be listening on this port -> a clean "unreachable".
    cfg = load_config(env={"UNAV_SERVER_PORT": "65500"}, root=Path("/repo"))
    report = health_report(cfg, check_server=True)
    assert report["server"]["status"] in {"unreachable", "ok"}
    assert report["server"]["url"] == "http://127.0.0.1:65500/"
