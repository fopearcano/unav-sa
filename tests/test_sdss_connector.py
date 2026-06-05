"""Tests for the SDSS connector (mocked astroquery / in-memory rows; no network)."""

import sys
import types

import numpy as np
import pytest
from astropy.table import Table

from unav_core.connectors import sdss
from unav_core.connectors.base import (
    AstroqueryNotInstalledError,
    ConnectorNetworkError,
    EmptyResultError,
    MalformedResponseError,
)
from unav_core.data import ObjectType
from unav_core.provenance import Provenance

_PROV = Provenance(source="SDSS")


# --- normalisation (in-memory rows) ---


def test_spectro_z_is_redshift() -> None:
    rows = [
        {
            "specobjid": 320932083,
            "ra": 150.0,
            "dec": 2.2,
            "z": 0.55,
            "class": "GALAXY",
            "modelMag_r": 18.3,
        },
        {"specobjid": 320932084, "ra": 150.1, "dec": 2.3, "z": 2.1, "class": "QSO"},
    ]
    objects = sdss.normalize_sdss_rows(rows, provenance=_PROV, spectro=True)
    assert objects[0].uid == "sdss:320932083"
    assert objects[0].source == "SDSS"
    assert objects[0].object_type is ObjectType.GALAXY
    assert objects[0].redshift == 0.55
    assert objects[0].apparent_magnitude == 18.3
    assert objects[1].object_type is ObjectType.QUASAR
    assert objects[1].redshift == 2.1


def test_photometric_z_is_not_redshift() -> None:
    # In photometric mode 'z' is the z-band magnitude, not a redshift.
    rows = [{"objid": 1237, "ra": 150.0, "dec": 2.2, "z": 19.4, "type": 3, "modelMag_r": 18.9}]
    obj = sdss.normalize_sdss_rows(rows, provenance=_PROV, spectro=False)[0]
    assert obj.redshift is None
    assert obj.object_type is ObjectType.GALAXY  # photometric type 3 -> galaxy
    assert obj.uid == "sdss:1237"


@pytest.mark.parametrize(
    "class_value,expected",
    [
        ("STAR", ObjectType.STAR),
        ("GALAXY", ObjectType.GALAXY),
        ("QSO", ObjectType.QUASAR),
        ("weird", ObjectType.UNKNOWN),
        (None, ObjectType.UNKNOWN),
    ],
)
def test_class_mapping(class_value, expected) -> None:
    row = {"specobjid": 1, "ra": 10.0, "dec": 10.0, "z": 0.1}
    if class_value is not None:
        row["class"] = class_value
    obj = sdss.normalize_sdss_rows([row], provenance=_PROV, spectro=True)[0]
    assert obj.object_type is expected


def test_uid_prefers_specobjid_then_objid() -> None:
    with_spec = {"specobjid": 99, "objid": 1, "ra": 1.0, "dec": 1.0, "class": "STAR"}
    assert sdss.normalize_sdss_rows([with_spec], provenance=_PROV)[0].uid == "sdss:99"
    only_obj = {"objid": 7, "ra": 1.0, "dec": 1.0, "class": "STAR"}
    assert sdss.normalize_sdss_rows([only_obj], provenance=_PROV)[0].uid == "sdss:7"


def test_missing_id_is_malformed() -> None:
    with pytest.raises(MalformedResponseError):
        sdss.normalize_sdss_rows([{"ra": 1.0, "dec": 1.0}], provenance=_PROV)


def test_missing_radec_is_malformed() -> None:
    with pytest.raises(MalformedResponseError):
        sdss.normalize_sdss_rows([{"specobjid": 1, "ra": 1.0}], provenance=_PROV)


def test_out_of_range_dec_is_malformed() -> None:
    rows = [{"specobjid": 1, "ra": 1.0, "dec": 999.0, "class": "STAR"}]
    with pytest.raises(MalformedResponseError):
        sdss.normalize_sdss_rows(rows, provenance=_PROV)


# --- fetch wiring (mocked astroquery.sdss) ---


def _sdss_table() -> Table:
    table = Table()
    table["specobjid"] = np.array([320932083, 320932084, 320932085], dtype="int64")
    table["ra"] = [150.0, 150.1, 150.2]
    table["dec"] = [2.2, 2.3, 2.4]
    table["z"] = [0.55, 2.1, 0.0001]
    table["class"] = ["GALAXY", "QSO", "STAR"]
    table["subclass"] = ["", "BROADLINE", ""]
    return table


def _install_fake_sdss(monkeypatch, table, *, raise_exc: Exception | None = None):
    captured: dict[str, object] = {}

    class FakeSDSS:
        @staticmethod
        def query_region(coordinates=None, **kwargs):
            captured["coordinates"] = coordinates
            captured.update(kwargs)
            if raise_exc is not None:
                raise raise_exc
            return table

    fake = types.ModuleType("astroquery.sdss")
    fake.SDSS = FakeSDSS
    monkeypatch.setitem(sys.modules, "astroquery", types.ModuleType("astroquery"))
    monkeypatch.setitem(sys.modules, "astroquery.sdss", fake)
    return captured


def test_fetch_normalizes(monkeypatch) -> None:
    captured = _install_fake_sdss(monkeypatch, _sdss_table())
    objects = sdss.fetch_sdss_region(150.0, 2.2, 0.05, limit=10)
    assert [o.object_type for o in objects] == [
        ObjectType.GALAXY,
        ObjectType.QUASAR,
        ObjectType.STAR,
    ]
    assert objects[0].redshift == 0.55
    assert captured["spectro"] is True


def test_fetch_truncates_to_limit(monkeypatch) -> None:
    _install_fake_sdss(monkeypatch, _sdss_table())
    objects = sdss.fetch_sdss_region(150.0, 2.2, 0.05, limit=2)
    assert len(objects) == 2


def test_fetch_none_result_is_empty(monkeypatch) -> None:
    _install_fake_sdss(monkeypatch, None)  # astroquery returns None for no matches
    with pytest.raises(EmptyResultError):
        sdss.fetch_sdss_region(150.0, 2.2, 0.05)


def test_fetch_network_failure(monkeypatch) -> None:
    _install_fake_sdss(monkeypatch, _sdss_table(), raise_exc=RuntimeError("503"))
    with pytest.raises(ConnectorNetworkError):
        sdss.fetch_sdss_region(150.0, 2.2, 0.05)


def test_fetch_radius_cap() -> None:
    with pytest.raises(ValueError):
        sdss.fetch_sdss_region(150.0, 2.2, 10.0)  # exceeds the 5 deg cap


def test_fetch_astroquery_missing(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "astroquery", None)
    monkeypatch.setitem(sys.modules, "astroquery.sdss", None)
    with pytest.raises(AstroqueryNotInstalledError):
        sdss.fetch_sdss_region(150.0, 2.2, 0.05)


def test_fetch_provenance(monkeypatch) -> None:
    _install_fake_sdss(monkeypatch, _sdss_table())
    objects = sdss.fetch_sdss_region(150.0, 2.2, 0.05, limit=10, data_release=17)
    provenance = objects[0].provenance
    assert provenance is not None
    assert provenance.source == "SDSS"
    assert provenance.catalog == "SDSS DR17"
    assert provenance.query_parameters["spectro"] is True
    assert provenance.retrieved_at is not None
