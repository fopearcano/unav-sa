"""Tests for Astropy-backed coordinate enrichment of CatalogObject."""

import pytest

from unav_core.astro.coordinates import radec_distance_to_cartesian
from unav_core.astro.enrich import enrich_object_coordinates
from unav_core.data import CatalogObject, ObjectType


def _star(**kwargs: object) -> CatalogObject:
    base: dict[str, object] = dict(uid="x", source="s", object_type=ObjectType.STAR)
    base.update(kwargs)
    return CatalogObject(**base)


def test_enrich_computes_xyz_from_radec_distance() -> None:
    obj = _star(ra_deg=45.0, dec_deg=30.0, distance_pc=10.0)
    enriched = enrich_object_coordinates(obj)
    expected = radec_distance_to_cartesian(45.0, 30.0, 10.0)
    assert (enriched.x, enriched.y, enriched.z) == pytest.approx(expected, abs=1e-9)
    assert all(v is not None and v == v for v in (enriched.x, enriched.y, enriched.z))  # finite


def test_enrich_does_not_mutate_input() -> None:
    obj = _star(ra_deg=45.0, dec_deg=30.0, distance_pc=10.0)
    enriched = enrich_object_coordinates(obj)
    assert obj.x is None and obj.y is None and obj.z is None  # original untouched
    assert enriched is not obj


def test_enrich_derives_distance_from_positive_parallax_and_marks_it() -> None:
    obj = _star(ra_deg=45.0, dec_deg=30.0, parallax_mas=100.0)  # 100 mas -> 10 pc
    enriched = enrich_object_coordinates(obj)
    assert enriched.distance_pc == pytest.approx(10.0, abs=1e-9)
    assert enriched.has_cartesian
    # The parallax-derived distance is approximate and is flagged for honesty.
    assert enriched.metadata.get("distance_from_parallax") is True


def test_enrich_keeps_existing_metadata_when_marking() -> None:
    obj = _star(ra_deg=45.0, dec_deg=30.0, parallax_mas=50.0, metadata={"band": "G"})
    enriched = enrich_object_coordinates(obj)
    assert enriched.metadata["band"] == "G"
    assert enriched.metadata["distance_from_parallax"] is True


def test_enrich_with_real_distance_does_not_mark_parallax() -> None:
    obj = _star(ra_deg=45.0, dec_deg=30.0, distance_pc=10.0, parallax_mas=100.0)
    enriched = enrich_object_coordinates(obj)
    assert "distance_from_parallax" not in enriched.metadata  # real distance, no flag


def test_enrich_skips_without_distance_or_parallax() -> None:
    obj = _star(ra_deg=45.0, dec_deg=30.0)
    result = enrich_object_coordinates(obj)
    assert result.has_cartesian is False
    assert result.distance_pc is None


def test_enrich_skips_nonpositive_parallax() -> None:
    obj = _star(ra_deg=45.0, dec_deg=30.0, parallax_mas=-2.0)
    assert enrich_object_coordinates(obj).has_cartesian is False


def test_enrich_skips_without_sky_position() -> None:
    obj = _star(distance_pc=10.0)  # distance but no ra/dec
    assert enrich_object_coordinates(obj).has_cartesian is False


def test_enrich_preserves_existing_cartesian() -> None:
    obj = _star(ra_deg=45.0, dec_deg=30.0, distance_pc=10.0, x=1.0, y=2.0, z=3.0)
    enriched = enrich_object_coordinates(obj)
    assert (enriched.x, enriched.y, enriched.z) == (1.0, 2.0, 3.0)


def test_enrich_can_disable_parallax_derivation() -> None:
    obj = _star(ra_deg=45.0, dec_deg=30.0, parallax_mas=100.0)
    enriched = enrich_object_coordinates(obj, derive_distance_from_parallax=False)
    assert enriched.has_cartesian is False
