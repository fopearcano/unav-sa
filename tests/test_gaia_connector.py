"""Tests for the Gaia connector using mocked astroquery responses (no network)."""

import sys
import types

import numpy as np
import pytest
from astropy.table import Table

from unav_core.connectors import gaia
from unav_core.connectors.base import (
    AstroqueryNotInstalledError,
    ConnectorNetworkError,
    EmptyResultError,
    MalformedResponseError,
)
from unav_core.data import ObjectType


def _gaia_table(masked: bool = True) -> Table:
    table = Table()
    table["source_id"] = np.array([4295806720, 34361129088], dtype="int64")
    table["ra"] = [45.0, 45.1]
    table["dec"] = [0.1, -0.2]
    if masked:
        table["parallax"] = np.ma.array([3.5, 0.0], mask=[False, True])
        table["radial_velocity"] = np.ma.array([12.0, 0.0], mask=[False, True])
    else:
        table["parallax"] = [3.5, 1.0]
        table["radial_velocity"] = [12.0, 5.0]
    table["phot_g_mean_mag"] = [11.2, 19.9]
    table["bp_rp"] = [0.8, 1.5]
    table["pmra"] = [1.1, -0.3]
    table["pmdec"] = [-2.2, 0.4]
    return table


def _install_fake_gaia(
    monkeypatch, table: Table | None = None, *, raise_exc: Exception | None = None
):
    captured: dict[str, object] = {}

    class FakeJob:
        def __init__(self, result: Table | None) -> None:
            self._result = result

        def get_results(self) -> Table | None:
            return self._result

    class FakeGaia:
        @staticmethod
        def launch_job(adql: str, *args, **kwargs):
            captured["adql"] = adql
            if raise_exc is not None:
                raise raise_exc
            return FakeJob(table)

    fake = types.ModuleType("astroquery.gaia")
    fake.Gaia = FakeGaia
    monkeypatch.setitem(sys.modules, "astroquery", types.ModuleType("astroquery"))
    monkeypatch.setitem(sys.modules, "astroquery.gaia", fake)
    return captured


def test_fetch_normalizes(monkeypatch) -> None:
    _install_fake_gaia(monkeypatch, _gaia_table())
    objects = gaia.fetch_gaia_region(45.0, 0.0, 0.1, limit=5)
    assert len(objects) == 2
    first = objects[0]
    assert first.uid == "gaia:4295806720"  # globally unique, source-prefixed
    assert first.native_id == "4295806720"  # source-native id
    assert first.source == "Gaia DR3"
    assert first.object_type is ObjectType.STAR
    assert (first.ra_deg, first.dec_deg) == (45.0, 0.1)
    assert first.parallax_mas == 3.5
    assert first.apparent_magnitude == 11.2
    assert first.color_index == 0.8
    assert first.radial_velocity_kms == 12.0
    assert first.metadata["gaia_source_id"] == 4295806720


def test_masked_fields_become_none(monkeypatch) -> None:
    _install_fake_gaia(monkeypatch, _gaia_table(masked=True))
    objects = gaia.fetch_gaia_region(45.0, 0.0, 0.1, limit=5)
    assert objects[1].parallax_mas is None
    assert objects[1].radial_velocity_kms is None


def test_distance_from_positive_parallax(monkeypatch) -> None:
    _install_fake_gaia(monkeypatch, _gaia_table(masked=False))
    objects = gaia.fetch_gaia_region(45.0, 0.0, 0.1, limit=5)
    assert objects[0].distance_pc == pytest.approx(1000.0 / 3.5, rel=1e-9)  # parallax 3.5 mas
    assert objects[1].distance_pc == pytest.approx(1000.0, rel=1e-9)  # parallax 1.0 mas


def test_no_distance_without_positive_parallax(monkeypatch) -> None:
    table = _gaia_table(masked=False)
    table["parallax"] = [-2.0, 0.0]  # negative + zero parallax -> no distance
    _install_fake_gaia(monkeypatch, table)
    objects = gaia.fetch_gaia_region(45.0, 0.0, 0.1, limit=5)
    assert objects[0].parallax_mas == -2.0  # kept (real noisy measurement)
    assert objects[0].distance_pc is None
    assert objects[1].distance_pc is None


def test_adql_region_and_limit(monkeypatch) -> None:
    captured = _install_fake_gaia(monkeypatch, _gaia_table())
    gaia.fetch_gaia_region(45.0, 0.0, 0.1, limit=5)
    adql = captured["adql"]
    assert "TOP 5" in adql
    assert "gaiadr3.gaia_source" in adql
    assert "CIRCLE('ICRS', 45.0, 0.0, 0.1)" in adql


def test_default_limit_is_500(monkeypatch) -> None:
    captured = _install_fake_gaia(monkeypatch, _gaia_table())
    gaia.fetch_gaia_region(45.0, 0.0, 0.1)
    assert "TOP 500" in captured["adql"]


def test_radius_cap_and_override(monkeypatch) -> None:
    _install_fake_gaia(monkeypatch, _gaia_table())
    with pytest.raises(ValueError):
        gaia.fetch_gaia_region(45.0, 0.0, 10.0)  # exceeds the 5 deg cap
    objects = gaia.fetch_gaia_region(45.0, 0.0, 10.0, allow_large_radius=True)
    assert len(objects) == 2


def test_hard_warning_above_5000(monkeypatch) -> None:
    _install_fake_gaia(monkeypatch, _gaia_table())
    with pytest.warns(UserWarning):
        gaia.fetch_gaia_region(45.0, 0.0, 0.1, limit=6000)


def test_astroquery_missing(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "astroquery", None)
    monkeypatch.setitem(sys.modules, "astroquery.gaia", None)
    with pytest.raises(AstroqueryNotInstalledError):
        gaia.fetch_gaia_region(45.0, 0.0, 0.1)


def test_network_failure(monkeypatch) -> None:
    _install_fake_gaia(monkeypatch, _gaia_table(), raise_exc=RuntimeError("connection reset"))
    with pytest.raises(ConnectorNetworkError):
        gaia.fetch_gaia_region(45.0, 0.0, 0.1)


def test_empty_result(monkeypatch) -> None:
    _install_fake_gaia(monkeypatch, _gaia_table()[:0])
    with pytest.raises(EmptyResultError):
        gaia.fetch_gaia_region(45.0, 0.0, 0.1)


def test_malformed_missing_source_id(monkeypatch) -> None:
    table = _gaia_table()
    table.remove_column("source_id")
    _install_fake_gaia(monkeypatch, table)
    with pytest.raises(MalformedResponseError):
        gaia.fetch_gaia_region(45.0, 0.0, 0.1)


def test_malformed_out_of_range_ra(monkeypatch) -> None:
    table = _gaia_table()
    table["ra"] = [999.0, 45.1]  # invalid -> fails schema validation
    _install_fake_gaia(monkeypatch, table)
    with pytest.raises(MalformedResponseError):
        gaia.fetch_gaia_region(45.0, 0.0, 0.1)


def test_provenance_attached(monkeypatch) -> None:
    _install_fake_gaia(monkeypatch, _gaia_table())
    objects = gaia.fetch_gaia_region(45.0, 0.0, 0.1, limit=5)
    provenance = objects[0].provenance
    assert provenance is not None
    assert provenance.source == "Gaia DR3"
    assert provenance.epoch == "J2016.0"
    assert provenance.query_parameters["limit"] == 5
    assert provenance.retrieved_at is not None
