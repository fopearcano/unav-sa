"""Tests for the deterministic sample catalog generator (offline, no network)."""

import pytest

from unav_core.astro.coordinates import radec_distance_to_cartesian
from unav_core.data import (
    CANONICAL_UNITS,
    CatalogObject,
    ObjectType,
    generate_sample_catalog,
    read_jsonl,
    write_sample_catalog,
)
from unav_core.data.sample_generator import DEFAULT_COUNT, MAX_COUNT
from unav_core.db import Database, import_objects

_SOLAR_TYPES = {ObjectType.PLANET, ObjectType.MOON, ObjectType.ASTEROID, ObjectType.COMET}


def test_default_count() -> None:
    objects = generate_sample_catalog()
    assert len(objects) == DEFAULT_COUNT
    assert all(isinstance(o, CatalogObject) for o in objects)


def test_count_is_respected() -> None:
    assert len(generate_sample_catalog(0)) == 0
    assert len(generate_sample_catalog(7, seed=1)) == 7
    assert len(generate_sample_catalog(250, seed=1)) == 250


def test_max_count_boundary() -> None:
    assert len(generate_sample_catalog(MAX_COUNT, seed=1)) == MAX_COUNT
    with pytest.raises(ValueError):
        generate_sample_catalog(MAX_COUNT + 1)
    with pytest.raises(ValueError):
        generate_sample_catalog(-1)


def test_determinism_same_seed() -> None:
    a = generate_sample_catalog(100, seed=42)
    b = generate_sample_catalog(100, seed=42)
    assert [o.model_dump(mode="json") for o in a] == [o.model_dump(mode="json") for o in b]


def test_different_seed_differs() -> None:
    a = generate_sample_catalog(100, seed=42)
    c = generate_sample_catalog(100, seed=43)
    assert [o.model_dump(mode="json") for o in a] != [o.model_dump(mode="json") for o in c]


def test_unique_uids() -> None:
    objects = generate_sample_catalog(500, seed=7)
    uids = [o.uid for o in objects]
    assert len(set(uids)) == len(uids)


def test_required_fields_present() -> None:
    for obj in generate_sample_catalog(100, seed=3):
        assert obj.uid
        assert obj.source.startswith("sample-")
        assert isinstance(obj.object_type, ObjectType)
        assert obj.name
        assert obj.ra_deg is not None and obj.dec_deg is not None
        assert obj.metadata.get("sample") is True
        assert obj.provenance is not None
        assert obj.provenance.source == obj.source
        # provenance must stay deterministic (no wall-clock timestamp).
        assert obj.provenance.retrieved_at is None


def test_distance_or_redshift_by_type() -> None:
    for obj in generate_sample_catalog(200, seed=9):
        if obj.object_type in {ObjectType.GALAXY, ObjectType.QUASAR}:
            assert obj.redshift is not None
        else:
            # stars, solar-system bodies and custom objects carry a distance.
            assert obj.distance_pc is not None


def test_all_categories_present() -> None:
    types = {o.object_type for o in generate_sample_catalog(100, seed=42)}
    assert {ObjectType.STAR, ObjectType.GALAXY, ObjectType.QUASAR, ObjectType.CUSTOM} <= types
    assert types & _SOLAR_TYPES  # at least one solar-system body


def test_coordinate_ranges_valid() -> None:
    for obj in generate_sample_catalog(300, seed=11):
        assert 0.0 <= obj.ra_deg < 360.0
        assert -90.0 <= obj.dec_deg <= 90.0


def test_write_and_read_roundtrip(tmp_path) -> None:
    path = tmp_path / "sample.jsonl"
    written = write_sample_catalog(path, 50, seed=5)
    assert written == 50
    restored = read_jsonl(path)
    assert len(restored) == 50
    assert restored[0].metadata.get("sample") is True


def test_write_is_deterministic(tmp_path) -> None:
    first = tmp_path / "a.jsonl"
    second = tmp_path / "b.jsonl"
    write_sample_catalog(first, 100, seed=42)
    write_sample_catalog(second, 100, seed=42)
    assert first.read_bytes() == second.read_bytes()


def test_imports_into_database() -> None:
    objects = generate_sample_catalog(100, seed=42)
    db = Database(":memory:")
    summary = import_objects(db, objects, dataset_name="sample")
    assert summary.inserted == 100
    assert summary.duplicates_in_file == 0
    assert db.count_objects() == 100
    db.dispose()


def test_enriches_cartesian_through_astropy_by_default() -> None:
    objects = generate_sample_catalog(200, seed=9)
    enriched = 0
    for obj in objects:
        if obj.distance_pc is not None:
            # Objects with a distance get Astropy-computed ICRS Cartesian x/y/z.
            assert obj.has_cartesian
            expected = radec_distance_to_cartesian(obj.ra_deg, obj.dec_deg, obj.distance_pc)
            assert (obj.x, obj.y, obj.z) == pytest.approx(expected, abs=1e-9)
            enriched += 1
        else:
            # Redshift-only objects (galaxies, quasars) stay sky-only.
            assert not obj.has_cartesian
    assert enriched > 0  # the sample really does contain usable 3D positions


def test_no_enrich_leaves_cartesian_unset() -> None:
    for obj in generate_sample_catalog(100, seed=42, enrich=False):
        assert obj.x is None and obj.y is None and obj.z is None


def test_provenance_records_frame_epoch_and_units() -> None:
    for obj in generate_sample_catalog(100, seed=42):
        prov = obj.provenance
        assert prov is not None
        assert prov.reference_frame == "ICRS"
        assert prov.epoch == "J2000.0"
        # The unit convention travels with the data (coordinate fields included).
        assert prov.units == CANONICAL_UNITS
        assert prov.units["x"] == "pc"
        assert prov.units["ra_deg"] == "deg"
