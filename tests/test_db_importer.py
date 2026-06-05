"""Tests for the JSONL -> SQLite importer."""

import pytest
from sqlalchemy import select

from unav_core.data import CatalogObject, ObjectType, write_jsonl
from unav_core.db import Database, import_jsonl_to_db, import_objects
from unav_core.db.schema import datasets_table, provenance_table
from unav_core.provenance.provenance import Provenance


def _objs() -> list[CatalogObject]:
    return [
        CatalogObject(
            uid="a",
            source="Gaia",
            object_type=ObjectType.STAR,
            ra_deg=10.0,
            dec_deg=20.0,
            parallax_mas=100.0,
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


def test_import_jsonl_file_roundtrip(tmp_path) -> None:
    jsonl = tmp_path / "c.jsonl"
    write_jsonl(_objs(), jsonl)
    db_file = tmp_path / "u.db"
    summary = import_jsonl_to_db(jsonl, db_file, "sample")
    assert summary.inserted == 2
    assert summary.parse_errors == 0

    reopened = Database(db_file)
    assert reopened.count_objects() == 2
    reopened.dispose()


def test_duplicate_uid_within_batch() -> None:
    db = Database(":memory:")
    objects = [
        CatalogObject(uid="x", source="s", object_type=ObjectType.STAR, ra_deg=1.0, dec_deg=2.0),
        CatalogObject(uid="x", source="s", object_type=ObjectType.STAR, ra_deg=3.0, dec_deg=4.0),
        CatalogObject(uid="y", source="s", object_type=ObjectType.STAR, ra_deg=5.0, dec_deg=6.0),
    ]
    summary = import_objects(db, objects, dataset_name="d")
    assert summary.duplicates_in_file == 1
    assert summary.inserted == 2
    assert db.count_objects() == 2
    db.dispose()


def test_duplicate_existing() -> None:
    db = Database(":memory:")
    first = import_objects(db, _objs(), dataset_name="first")
    assert first.inserted == 2
    second = import_objects(db, _objs(), dataset_name="second")
    assert second.inserted == 0
    assert second.duplicates_existing == 2
    assert db.count_objects() == 2
    db.dispose()


def test_parse_errors(tmp_path) -> None:
    jsonl = tmp_path / "bad.jsonl"
    jsonl.write_text(
        "\n".join(
            [
                '{"uid":"ok","source":"s","object_type":"star","ra_deg":1.0,"dec_deg":2.0}',
                "{not json}",
                '{"uid":"baddec","source":"s","object_type":"star","dec_deg":999.0}',
            ]
        ),
        encoding="utf-8",
    )
    db = Database(":memory:")
    summary = import_jsonl_to_db(jsonl, ":memory:", "d", database=db)
    assert summary.parse_errors == 2
    assert summary.inserted == 1
    db.dispose()


def test_enrich_on_import(tmp_path) -> None:
    jsonl = tmp_path / "e.jsonl"
    write_jsonl(
        [
            CatalogObject(
                uid="s",
                source="Gaia",
                object_type=ObjectType.STAR,
                ra_deg=45.0,
                dec_deg=30.0,
                parallax_mas=100.0,
            )
        ],
        jsonl,
    )
    db = Database(":memory:")
    import_jsonl_to_db(jsonl, ":memory:", "d", enrich=True, database=db)
    obj = db.fetch_objects()[0]
    assert obj.has_cartesian
    assert obj.distance_pc == pytest.approx(10.0, abs=1e-9)
    db.dispose()


def test_full_fields_and_provenance_roundtrip() -> None:
    # The objects table persists the full scalar record + per-object provenance,
    # so the inspector (GET /objects/{uid}) can show Gaia fields and provenance.
    db = Database(":memory:")
    obj = CatalogObject(
        uid="gaia:1",
        source="Gaia DR3",
        object_type=ObjectType.STAR,
        ra_deg=10.0,
        dec_deg=20.0,
        parallax_mas=5.0,
        distance_pc=200.0,
        apparent_magnitude=9.5,
        color_index=0.7,
        proper_motion_ra_masyr=1.0,
        proper_motion_dec_masyr=-2.0,
        radial_velocity_kms=10.0,
        provenance=Provenance(source="Gaia DR3", catalog="Gaia DR3", epoch="J2016.0"),
    )
    import_objects(db, [obj], dataset_name="g")
    fetched = db.fetch_objects()[0]
    assert fetched.color_index == 0.7
    assert fetched.proper_motion_ra_masyr == 1.0
    assert fetched.proper_motion_dec_masyr == -2.0
    assert fetched.radial_velocity_kms == 10.0
    assert fetched.distance_pc == 200.0
    assert fetched.provenance is not None
    assert fetched.provenance.source == "Gaia DR3"
    assert fetched.provenance.epoch == "J2016.0"
    db.dispose()


def test_dataset_and_provenance_recorded() -> None:
    db = Database(":memory:")
    summary = import_objects(db, _objs(), dataset_name="ds")
    with db.connect() as conn:
        datasets = conn.execute(select(datasets_table)).all()
        provenances = conn.execute(select(provenance_table)).all()
    assert len(datasets) == 1
    assert len(provenances) == 1
    assert datasets[0]._mapping["dataset_id"] == summary.dataset_id
    assert provenances[0]._mapping["dataset_id"] == summary.dataset_id
    db.dispose()


def test_summary_render() -> None:
    db = Database(":memory:")
    summary = import_objects(db, _objs(), dataset_name="render-me")
    text = summary.render()
    assert "render-me" in text
    assert "inserted" in text
    db.dispose()
