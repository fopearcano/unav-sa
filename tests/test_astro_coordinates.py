"""Tests for the Astropy-backed coordinate helpers, frames and enrichment."""

import pytest

from unav_core.astro import coordinates as C
from unav_core.astro import frames
from unav_core.astro.enrich import enrich_object_coordinates
from unav_core.data import CatalogObject, ObjectType


def test_skycoord_from_radec_basic() -> None:
    sc = C.skycoord_from_radec(123.4, -5.6)
    assert sc.ra.deg == pytest.approx(123.4, abs=1e-9)
    assert sc.dec.deg == pytest.approx(-5.6, abs=1e-9)


def test_skycoord_with_distance() -> None:
    sc = C.skycoord_from_radec(10.0, 20.0, distance_pc=5.0)
    assert sc.distance.pc == pytest.approx(5.0, abs=1e-9)


@pytest.mark.parametrize(
    "ra,dec,expected",
    [
        (0.0, 0.0, (1.0, 0.0, 0.0)),
        (90.0, 0.0, (0.0, 1.0, 0.0)),
        (0.0, 90.0, (0.0, 0.0, 1.0)),
    ],
)
def test_cartesian_directions(ra: float, dec: float, expected: tuple[float, float, float]) -> None:
    assert C.radec_distance_to_cartesian(ra, dec, 1.0) == pytest.approx(expected, abs=1e-9)


def test_cartesian_roundtrip() -> None:
    ra, dec, d = 123.456, -41.2, 12.5
    x, y, z = C.radec_distance_to_cartesian(ra, dec, d)
    ra2, dec2, d2 = C.cartesian_to_radec_distance(x, y, z)
    assert ra2 == pytest.approx(ra, abs=1e-7)
    assert dec2 == pytest.approx(dec, abs=1e-7)
    assert d2 == pytest.approx(d, abs=1e-7)


def test_icrs_to_galactic_north_pole() -> None:
    # The ICRS position of the north galactic pole maps to b ~ +90 deg.
    _, b = C.icrs_to_galactic(192.85948, 27.12825)
    assert b == pytest.approx(90.0, abs=1e-3)


def test_galactic_icrs_roundtrip() -> None:
    lon, lat = 121.7, 29.8
    ra, dec = C.galactic_to_icrs(lon, lat)
    lon2, lat2 = C.icrs_to_galactic(ra, dec)
    assert lon2 == pytest.approx(lon, abs=1e-7)
    assert lat2 == pytest.approx(lat, abs=1e-7)


@pytest.mark.parametrize(
    "a,b,sep",
    [
        ((0.0, 0.0), (0.0, 90.0), 90.0),
        ((0.0, 0.0), (1.0, 0.0), 1.0),
        ((0.0, 0.0), (180.0, 0.0), 180.0),
        ((10.0, 20.0), (10.0, 20.0), 0.0),
    ],
)
def test_angular_separation(a: tuple[float, float], b: tuple[float, float], sep: float) -> None:
    assert C.angular_separation(a[0], a[1], b[0], b[1]) == pytest.approx(sep, abs=1e-6)
    # The explicit _deg alias is the same function and returns degrees.
    assert C.angular_separation_deg(a[0], a[1], b[0], b[1]) == pytest.approx(sep, abs=1e-6)


# --- frames registry ---


def test_supported_frames_and_default() -> None:
    assert "icrs" in frames.SUPPORTED_FRAMES
    assert "galactic" in frames.SUPPORTED_FRAMES
    assert frames.DEFAULT_FRAME == "icrs"


def test_normalize_frame_name() -> None:
    assert frames.normalize_frame_name("ICRS") == "icrs"
    assert frames.normalize_frame_name(" Galactic ") == "galactic"
    with pytest.raises(ValueError):
        frames.normalize_frame_name("bogus")


def test_get_frame_returns_astropy_class() -> None:
    from astropy.coordinates import ICRS, Galactic

    assert frames.get_frame("icrs") is ICRS
    assert frames.get_frame("galactic") is Galactic


# --- coordinate enrichment ---


def _star(**kwargs: object) -> CatalogObject:
    base: dict[str, object] = dict(uid="x", source="s", object_type=ObjectType.STAR)
    base.update(kwargs)
    return CatalogObject(**base)


def test_enrich_from_distance() -> None:
    obj = _star(ra_deg=45.0, dec_deg=30.0, distance_pc=10.0)
    enriched = enrich_object_coordinates(obj)
    expected = C.radec_distance_to_cartesian(45.0, 30.0, 10.0)
    assert (enriched.x, enriched.y, enriched.z) == pytest.approx(expected, abs=1e-9)
    assert obj.x is None  # input is not mutated


def test_enrich_derives_distance_from_parallax() -> None:
    obj = _star(ra_deg=45.0, dec_deg=30.0, parallax_mas=100.0)  # 100 mas -> 10 pc
    enriched = enrich_object_coordinates(obj)
    assert enriched.distance_pc == pytest.approx(10.0, abs=1e-9)
    assert enriched.has_cartesian


def test_enrich_skips_without_distance() -> None:
    obj = _star(ra_deg=45.0, dec_deg=30.0)
    assert enrich_object_coordinates(obj).has_cartesian is False


def test_enrich_skips_nonpositive_parallax() -> None:
    obj = _star(ra_deg=45.0, dec_deg=30.0, parallax_mas=-2.0)
    assert enrich_object_coordinates(obj).has_cartesian is False


def test_enrich_preserves_existing_cartesian() -> None:
    obj = _star(ra_deg=45.0, dec_deg=30.0, distance_pc=10.0, x=1.0, y=2.0, z=3.0)
    enriched = enrich_object_coordinates(obj)
    assert (enriched.x, enriched.y, enriched.z) == (1.0, 2.0, 3.0)


def test_enrich_can_disable_parallax_derivation() -> None:
    obj = _star(ra_deg=45.0, dec_deg=30.0, parallax_mas=100.0)
    enriched = enrich_object_coordinates(obj, derive_distance_from_parallax=False)
    assert enriched.has_cartesian is False
