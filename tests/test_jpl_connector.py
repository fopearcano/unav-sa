"""Tests for the JPL Horizons connector using mocked astroquery (no network)."""

import sys
import types

import pytest
from astropy.table import Table

from unav_core.connectors import jpl
from unav_core.connectors.base import (
    AstroqueryNotInstalledError,
    ConnectorNetworkError,
    EmptyResultError,
    MalformedResponseError,
)
from unav_core.data import ObjectType


def _jpl_table(
    ra: float = 150.5,
    dec: float = -12.3,
    delta: float = 1.52,
    mag: float = -0.5,
    targetname: str = "Mars (499)",
) -> Table:
    table = Table()
    table["targetname"] = [targetname]
    table["RA"] = [ra]
    table["DEC"] = [dec]
    table["delta"] = [delta]
    table["V"] = [mag]
    return table


def _install_fake_horizons(
    monkeypatch, table: Table | None = None, *, raise_exc: Exception | None = None
):
    captured: dict[str, object] = {}

    class FakeHorizons:
        def __init__(self, id=None, location=None, epochs=None) -> None:
            captured["id"] = id
            captured["location"] = location
            captured["epochs"] = epochs

        def ephemerides(self, *args, **kwargs):
            if raise_exc is not None:
                raise raise_exc
            return table

    fake = types.ModuleType("astroquery.jplhorizons")
    fake.Horizons = FakeHorizons
    monkeypatch.setitem(sys.modules, "astroquery", types.ModuleType("astroquery"))
    monkeypatch.setitem(sys.modules, "astroquery.jplhorizons", fake)
    return captured


def test_fetch_body_normalizes(monkeypatch) -> None:
    captured = _install_fake_horizons(monkeypatch, _jpl_table())
    obj = jpl.fetch_jpl_body("499", "2451545.0", "@sun", object_type="planet")
    assert obj.uid == "jpl:499:2451545.0"
    assert obj.source == "JPL Horizons"
    assert obj.object_type is ObjectType.PLANET
    assert obj.name == "Mars (499)"
    assert (obj.ra_deg, obj.dec_deg) == (150.5, -12.3)
    assert obj.apparent_magnitude == -0.5
    assert obj.metadata["distance_au"] == 1.52
    assert obj.metadata["center"] == "@sun"
    assert obj.metadata["epoch"] == "2451545.0"
    assert obj.distance_pc is not None and obj.distance_pc > 0.0
    assert obj.has_cartesian  # enriched ICRS x/y/z -> viewable in 3D
    assert captured["id"] == "499"
    assert captured["location"] == "@sun"
    assert captured["epochs"] == 2451545.0  # numeric epoch passed through as JD


def test_body_xyz_enriched(monkeypatch) -> None:
    _install_fake_horizons(monkeypatch, _jpl_table())
    obj = jpl.fetch_jpl_body("Mars", "2451545.0", object_type="planet")
    assert obj.x is not None and obj.y is not None and obj.z is not None


def test_classify_body() -> None:
    assert jpl.classify_body("Mars") is ObjectType.PLANET
    assert jpl.classify_body("earth") is ObjectType.PLANET
    assert jpl.classify_body("Pluto") is ObjectType.PLANET  # grouped with planets
    assert jpl.classify_body("Moon") is ObjectType.MOON
    assert jpl.classify_body("499") is ObjectType.UNKNOWN  # numeric id -> unknown
    assert jpl.classify_body("Ceres") is ObjectType.UNKNOWN


def test_iso_epoch_converted_to_jd(monkeypatch) -> None:
    captured = _install_fake_horizons(monkeypatch, _jpl_table())
    jpl.fetch_jpl_body("499", "2000-01-01T12:00:00", object_type="planet")
    assert captured["epochs"] == pytest.approx(2451545.0, abs=1e-6)


def test_object_type_coercion(monkeypatch) -> None:
    _install_fake_horizons(monkeypatch, _jpl_table())
    assert jpl.fetch_jpl_body("1", "2451545.0", object_type="asteroid").object_type is (
        ObjectType.ASTEROID
    )
    assert jpl.fetch_jpl_body("1", "2451545.0").object_type is ObjectType.UNKNOWN


def test_solar_system_mapping(monkeypatch) -> None:
    _install_fake_horizons(monkeypatch, _jpl_table())
    objects = jpl.fetch_jpl_solar_system({"499": "planet", "Ceres": "asteroid"}, "2451545.0")
    assert [o.uid for o in objects] == ["jpl:499:2451545.0", "jpl:Ceres:2451545.0"]
    assert {o.object_type for o in objects} == {ObjectType.PLANET, ObjectType.ASTEROID}


def test_solar_system_sequence_classifies_by_name(monkeypatch) -> None:
    _install_fake_horizons(monkeypatch, _jpl_table())
    objects = jpl.fetch_jpl_solar_system(["Mars", "Moon", "599"], "2451545.0")
    by_body = {o.metadata["body"]: o.object_type for o in objects}
    assert by_body["Mars"] is ObjectType.PLANET
    assert by_body["Moon"] is ObjectType.MOON
    assert by_body["599"] is ObjectType.UNKNOWN  # numeric id -> unknown


def test_astroquery_missing(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "astroquery", None)
    monkeypatch.setitem(sys.modules, "astroquery.jplhorizons", None)
    with pytest.raises(AstroqueryNotInstalledError):
        jpl.fetch_jpl_body("499", "2451545.0")


def test_network_failure(monkeypatch) -> None:
    _install_fake_horizons(monkeypatch, _jpl_table(), raise_exc=RuntimeError("timeout"))
    with pytest.raises(ConnectorNetworkError):
        jpl.fetch_jpl_body("499", "2451545.0")


def test_empty_result(monkeypatch) -> None:
    _install_fake_horizons(monkeypatch, _jpl_table()[:0])
    with pytest.raises(EmptyResultError):
        jpl.fetch_jpl_body("499", "2451545.0")


def test_malformed_missing_radec(monkeypatch) -> None:
    table = _jpl_table()
    table.remove_column("RA")
    _install_fake_horizons(monkeypatch, table)
    with pytest.raises(MalformedResponseError):
        jpl.fetch_jpl_body("499", "2451545.0")


def test_provenance_attached(monkeypatch) -> None:
    _install_fake_horizons(monkeypatch, _jpl_table())
    obj = jpl.fetch_jpl_body("499", "2451545.0", object_type="planet")
    provenance = obj.provenance
    assert provenance is not None
    assert provenance.source == "JPL Horizons"
    assert provenance.query_parameters["body"] == "499"
    assert provenance.retrieved_at is not None
