"""Tests for the local SQLite database: schema, indexes and query functions."""

import pytest
from sqlalchemy import inspect

from unav_core.data import CatalogObject, ObjectType
from unav_core.db import (
    Database,
    brightest_objects,
    filter_by_source,
    filter_by_type,
    highest_redshift_objects,
    import_objects,
    nearest_objects,
    objects_within_distance,
    search_by_name,
)


def _sample_objects() -> list[CatalogObject]:
    return [
        CatalogObject(
            uid="vega",
            source="Hipparcos",
            object_type=ObjectType.STAR,
            name="Vega",
            ra_deg=279.23,
            dec_deg=38.78,
            apparent_magnitude=0.03,
            x=1.0,
            y=0.0,
            z=0.0,
            metadata={"common_name": "Vega"},
        ),
        CatalogObject(
            uid="sirius",
            source="Hipparcos",
            object_type=ObjectType.STAR,
            name="Sirius",
            ra_deg=101.29,
            dec_deg=-16.72,
            apparent_magnitude=-1.46,
            x=0.0,
            y=1.0,
            z=0.0,
        ),
        CatalogObject(
            uid="m87",
            source="NED",
            object_type=ObjectType.GALAXY,
            name="Virgo A",
            ra_deg=187.71,
            dec_deg=12.39,
            redshift=0.0043,
            apparent_magnitude=8.6,
            x=0.0,
            y=0.0,
            z=5.0,
        ),
        CatalogObject(
            uid="3c273",
            source="SDSS",
            object_type=ObjectType.QUASAR,
            name="3C 273",
            ra_deg=187.28,
            dec_deg=2.05,
            redshift=0.158,
            apparent_magnitude=12.9,
        ),
    ]


@pytest.fixture
def db() -> Database:
    database = Database(":memory:")
    import_objects(database, _sample_objects(), dataset_name="test")
    yield database
    database.dispose()


def test_tables_created(db: Database) -> None:
    names = set(inspect(db.engine).get_table_names())
    assert {"objects", "metadata", "datasets", "provenance"} <= names


def test_indexes_created(db: Database) -> None:
    index_cols = {tuple(ix["column_names"]) for ix in inspect(db.engine).get_indexes("objects")}
    expected = [
        ("source",),
        ("object_type",),
        ("ra_deg", "dec_deg"),
        ("x",),
        ("y",),
        ("z",),
        ("distance_pc",),
        ("redshift",),
        ("apparent_magnitude",),
    ]
    for cols in expected:
        assert cols in index_cols, f"missing index on {cols}"


def test_count(db: Database) -> None:
    assert db.count_objects() == 4


def test_search_by_name_case_insensitive(db: Database) -> None:
    assert {o.uid for o in search_by_name(db, "VEGA")} == {"vega"}
    assert {o.uid for o in search_by_name(db, "3c")} == {"3c273"}


def test_filter_by_source(db: Database) -> None:
    assert {o.uid for o in filter_by_source(db, "Hipparcos")} == {"vega", "sirius"}


def test_filter_by_type_accepts_enum_and_str(db: Database) -> None:
    assert {o.uid for o in filter_by_type(db, ObjectType.GALAXY)} == {"m87"}
    assert {o.uid for o in filter_by_type(db, "quasar")} == {"3c273"}


def test_brightest_ordering(db: Database) -> None:
    result = brightest_objects(db, limit=3)
    mags = [o.apparent_magnitude for o in result]
    assert mags == sorted(mags)
    assert result[0].uid == "sirius"  # -1.46 is the brightest


def test_highest_redshift_ordering(db: Database) -> None:
    result = highest_redshift_objects(db, limit=2)
    assert result[0].uid == "3c273"  # 0.158 > 0.0043


def test_nearest_objects(db: Database) -> None:
    result = nearest_objects(db, 0.9, 0.0, 0.0, limit=1)  # near vega at (1,0,0)
    assert result[0].uid == "vega"


def test_objects_within_distance(db: Database) -> None:
    near = {o.uid for o in objects_within_distance(db, 1.0, 0.0, 0.0, 0.5)}
    assert near == {"vega"}
    # vega (1,0,0) and sirius (0,1,0) are ~1.414 apart; m87 (0,0,5) is far.
    wider = {o.uid for o in objects_within_distance(db, 1.0, 0.0, 0.0, 1.5)}
    assert wider == {"vega", "sirius"}


def test_metadata_roundtrip(db: Database) -> None:
    assert search_by_name(db, "vega")[0].metadata == {"common_name": "Vega"}
    assert search_by_name(db, "sirius")[0].metadata == {}  # no metadata stored


def test_objects_without_cartesian_excluded_from_3d(db: Database) -> None:
    # 3c273 has no x/y/z and must never appear in 3D proximity results.
    assert all(o.uid != "3c273" for o in nearest_objects(db, 0.0, 0.0, 0.0, limit=10))
