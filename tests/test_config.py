"""Tests for local configuration loading and .env parsing."""

import os
from pathlib import Path

from unav_core.config import apply_dotenv, load_config, parse_dotenv


def test_defaults_relative_to_root() -> None:
    cfg = load_config(env={}, root=Path("/repo"))
    assert cfg.data_dir == Path("/repo/data")
    assert cfg.database_path == Path("/repo/data/unav.db")
    assert cfg.cache_dir == Path("/repo/data/cache")
    assert cfg.samples_dir == Path("/repo/samples")
    assert cfg.default_query_limit == 500
    assert cfg.default_max_radius_deg == 5.0
    assert cfg.server_host == "127.0.0.1"
    assert cfg.server_port == 8765


def test_env_overrides() -> None:
    env = {
        "UNAV_DATA_DIR": "/custom/data",
        "UNAV_QUERY_LIMIT": "42",
        "UNAV_MAX_RADIUS_DEG": "2.5",
        "UNAV_SERVER_HOST": "0.0.0.0",
        "UNAV_SERVER_PORT": "9000",
    }
    cfg = load_config(env=env, root=Path("/repo"))
    assert cfg.data_dir == Path("/custom/data")
    assert cfg.database_path == Path("/custom/data/unav.db")  # DB follows DATA_DIR
    assert cfg.cache_dir == Path("/custom/data/cache")
    assert cfg.default_query_limit == 42
    assert cfg.default_max_radius_deg == 2.5
    assert cfg.server_host == "0.0.0.0"
    assert cfg.server_port == 9000


def test_explicit_db_path_overrides_data_dir() -> None:
    cfg = load_config(env={"UNAV_DB_PATH": "/tmp/x.db"}, root=Path("/repo"))
    assert cfg.database_path == Path("/tmp/x.db")


def test_properties_and_as_dict() -> None:
    cfg = load_config(env={}, root=Path("/repo"))
    assert cfg.sample_catalog_path == Path("/repo/samples/sample_catalog.jsonl")
    assert cfg.server_url == "http://127.0.0.1:8765/"
    assert cfg.as_dict()["database_path"] == "/repo/data/unav.db"


def test_ensure_dirs(tmp_path) -> None:
    cfg = load_config(env={"UNAV_DATA_DIR": str(tmp_path / "d")}, root=tmp_path)
    cfg.ensure_dirs()
    assert (tmp_path / "d").is_dir()
    assert (tmp_path / "d" / "cache").is_dir()


def test_parse_dotenv() -> None:
    body = '# comment\n\nUNAV_SERVER_PORT=9000\nUNAV_DATA_DIR="/x/y"\nbad line\n'
    parsed = parse_dotenv(body)
    assert parsed == {"UNAV_SERVER_PORT": "9000", "UNAV_DATA_DIR": "/x/y"}


def test_apply_dotenv_respects_existing(tmp_path, monkeypatch) -> None:
    (tmp_path / ".env").write_text("UNAV_TEST_PORT=9999\nUNAV_PRESET=fromfile\n", encoding="utf-8")
    monkeypatch.setenv("UNAV_PRESET", "original")  # pre-set -> must be preserved
    applied = apply_dotenv(tmp_path)
    try:
        assert applied == {"UNAV_TEST_PORT": "9999"}
        assert os.environ["UNAV_TEST_PORT"] == "9999"
        assert os.environ["UNAV_PRESET"] == "original"
    finally:
        os.environ.pop("UNAV_TEST_PORT", None)


def test_apply_dotenv_missing_file_is_noop(tmp_path) -> None:
    assert apply_dotenv(tmp_path) == {}
