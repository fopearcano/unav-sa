"""Tests for the DB query functions, get_db_info and the db.models aggregation."""

import pytest

from unav_core.data import CatalogObject, ObjectType
from unav_core.db import (
    Database,
    brightest_objects,
    filter_by_source,
    filter_by_type,
    get_db_info,
    get_object,
    highest_redshift_objects,
    import_objects,
    objects_within_distance,
    search_by_name,
)
from unav_core.db.queries import objects_in_sky_box


def _objects() -> list[CatalogObject]:
    return [
        CatalogObject(
            uid="gaia:1",
            source="Gaia DR3",
            object_type=ObjectType.STAR,
            name="Vega",
            ra_deg=279.23,
            dec_deg=38.78,
            apparent_magnitude=0.03,
            x=1.0,
            y=0.0,
            z=0.0,
        ),
        CatalogObject(
            uid="gaia:2",
            source="Gaia DR3",
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
            uid="ned:m87",
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
            uid="sdss:3c273",
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
def db():
    database = Database(":memory:")
    import_objects(database, _objects(), dataset_name="test")
    yield database
    database.dispose()


def test_get_object_by_uid(db) -> None:
    assert get_object(db, "gaia:1").name == "Vega"
    assert get_object(db, "missing") is None


def test_search_by_name_case_insensitive(db) -> None:
    assert {o.uid for o in search_by_name(db, "VEGA")} == {"gaia:1"}
    assert {o.uid for o in search_by_name(db, "3c")} == {"sdss:3c273"}


def test_filter_by_source_and_type(db) -> None:
    assert {o.uid for o in filter_by_source(db, "Gaia DR3")} == {"gaia:1", "gaia:2"}
    assert {o.uid for o in filter_by_type(db, ObjectType.GALAXY)} == {"ned:m87"}
    assert {o.uid for o in filter_by_type(db, "quasar")} == {"sdss:3c273"}


def test_brightest_and_highest_redshift(db) -> None:
    assert brightest_objects(db, limit=1)[0].uid == "gaia:2"  # -1.46 is brightest
    assert highest_redshift_objects(db, limit=1)[0].uid == "sdss:3c273"  # 0.158 > 0.0043


def test_objects_within_distance_is_spatial(db) -> None:
    # objects_within_distance is a Cartesian box+radius around (x, y, z).
    near = {o.uid for o in objects_within_distance(db, 1.0, 0.0, 0.0, 0.5)}
    assert near == {"gaia:1"}
    wider = {o.uid for o in objects_within_distance(db, 1.0, 0.0, 0.0, 1.5)}
    assert wider == {"gaia:1", "gaia:2"}  # sqrt(2) apart


def test_objects_in_sky_box(db) -> None:
    box = {o.uid for o in objects_in_sky_box(db, 180.0, 190.0, 0.0, 20.0)}
    assert box == {"ned:m87", "sdss:3c273"}


def test_get_db_info(tmp_path) -> None:
    db_path = tmp_path / "unav.db"
    database = Database(db_path)
    import_objects(database, _objects(), dataset_name="test")
    database.dispose()

    info = get_db_info(db_path)  # accepts a Path
    assert info["object_count"] == 4
    assert info["dataset_count"] == 1
    assert info["by_source"]["Gaia DR3"] == 2
    assert info["by_type"]["star"] == 2
    assert info["by_type"]["galaxy"] == 1


def test_db_models_aggregation_imports() -> None:
    from unav_core.db import models

    assert set(models.TABLES) >= {"objects", "metadata", "datasets", "provenance"}
    assert models.objects_table.name == "objects"
    assert models.CatalogObject is CatalogObject
