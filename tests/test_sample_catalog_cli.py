"""CLI tests for the sample-catalog generator and the offline sample-DB script.

All offline: generation + import only, no network.
"""

import importlib.util
from pathlib import Path

from typer.testing import CliRunner

from unav_core.data.io import read_jsonl
from unav_core.db import get_db_info

_REPO_ROOT = Path(__file__).resolve().parent.parent
_runner = CliRunner()


def _load(rel_path: str):
    path = _REPO_ROOT / rel_path
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generate_cli_writes_requested_count(tmp_path) -> None:
    tool = _load("tools/generate_sample_catalog.py")
    out = tmp_path / "c.jsonl"
    result = _runner.invoke(tool.app, ["--count", "20", "--seed", "7", "--output", str(out)])
    assert result.exit_code == 0, result.output
    assert len(read_jsonl(out)) == 20


def test_generate_cli_is_deterministic(tmp_path) -> None:
    tool = _load("tools/generate_sample_catalog.py")
    a, b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    for out in (a, b):
        result = _runner.invoke(tool.app, ["--count", "50", "--seed", "42", "--output", str(out)])
        assert result.exit_code == 0, result.output
    assert a.read_bytes() == b.read_bytes()  # same seed -> byte-identical


def test_generate_cli_no_enrich(tmp_path) -> None:
    tool = _load("tools/generate_sample_catalog.py")
    out = tmp_path / "c.jsonl"
    result = _runner.invoke(
        tool.app, ["--count", "10", "--seed", "1", "--no-enrich", "--output", str(out)]
    )
    assert result.exit_code == 0, result.output
    assert all(o.x is None for o in read_jsonl(out))  # no x/y/z without enrichment


def test_create_sample_db_cli_imports_and_summarises(tmp_path) -> None:
    script = _load("scripts/create_sample_db.py")
    catalog = tmp_path / "sample.jsonl"
    db = tmp_path / "unav_sample.db"
    result = _runner.invoke(
        script.app,
        ["--catalog", str(catalog), "--db", str(db), "--count", "100", "--seed", "42"],
    )
    assert result.exit_code == 0, result.output
    assert catalog.exists() and db.exists()

    info = get_db_info(db)
    assert info["object_count"] == 100
    assert info["dataset_count"] == 1
    assert info["by_type"]["star"] == 50  # source/type counts available
    assert "sample-gaia" in info["by_source"]
