"""Tests for JSONL import/export and file validation."""

from datetime import datetime

import pytest

from unav_core.data import (
    CatalogObject,
    ObjectType,
    read_jsonl,
    validate_jsonl,
    write_jsonl,
)
from unav_core.provenance import Provenance


def _sample_objects() -> list[CatalogObject]:
    return [
        CatalogObject(
            uid="a",
            source="Gaia",
            object_type=ObjectType.STAR,
            ra_deg=10.0,
            dec_deg=20.0,
            parallax_mas=5.0,
            provenance=Provenance.now("Gaia", catalog="Gaia DR3"),
        ),
        CatalogObject(
            uid="b",
            source="Gaia",
            object_type=ObjectType.GALAXY,
            ra_deg=11.0,
            dec_deg=21.0,
            redshift=0.1,
        ),
    ]


def test_write_then_read_roundtrip(tmp_path) -> None:
    path = tmp_path / "objs.jsonl"
    written = write_jsonl(_sample_objects(), path)
    assert written == 2

    restored = read_jsonl(path)
    assert [o.uid for o in restored] == ["a", "b"]
    assert restored[0].ra_deg == 10.0
    assert restored[0].object_type is ObjectType.STAR
    assert restored[0].provenance is not None
    assert restored[0].provenance.catalog == "Gaia DR3"
    assert isinstance(restored[0].provenance.retrieved_at, datetime)


def test_write_creates_parent_dirs(tmp_path) -> None:
    path = tmp_path / "nested" / "deep" / "objs.jsonl"
    write_jsonl(_sample_objects(), path)
    assert path.exists()


def test_line_count_matches(tmp_path) -> None:
    path = tmp_path / "o.jsonl"
    write_jsonl(_sample_objects(), path)
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 2


def test_validate_jsonl_clean_file(tmp_path) -> None:
    path = tmp_path / "clean.jsonl"
    write_jsonl(_sample_objects(), path)
    report = validate_jsonl(path)
    assert report.ok
    assert report.errors == []


def test_validate_jsonl_detects_bad_lines(tmp_path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text(
        "\n".join(
            [
                '{"uid": "ok", "source": "s", "object_type": "star",'
                ' "ra_deg": 1.0, "dec_deg": 2.0}',
                "{not json}",
                '{"uid": "baddec", "source": "s", "object_type": "star", "dec_deg": 999.0}',
                '{"uid": "nopos", "source": "s", "object_type": "star"}',
            ]
        ),
        encoding="utf-8",
    )
    report = validate_jsonl(path)
    assert not report.ok
    codes = {issue.code for issue in report.issues}
    assert "json_error" in codes  # the "{not json}" line
    assert "schema_error" in codes  # dec_deg out of range
    assert "missing_coordinates" in codes  # the "nopos" object parsed but has no position


def test_read_jsonl_raises_on_bad_line(tmp_path) -> None:
    path = tmp_path / "broken.jsonl"
    path.write_text("{not json}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        read_jsonl(path)
