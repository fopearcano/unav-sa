"""Tests for the DESI connector foundation (in-memory rows + local file; no network)."""

import numpy as np
import pytest
from astropy.table import Table

from unav_core.connectors import desi
from unav_core.connectors.base import (
    ConnectorNotSupportedError,
    EmptyResultError,
    MalformedResponseError,
)
from unav_core.data import ObjectType
from unav_core.provenance import Provenance

_PROV = Provenance(source="DESI")


# --- normalisation (in-memory rows; DESI columns are upper-case) ---


def test_normalize_rows() -> None:
    rows = [
        {
            "TARGETID": 39627,
            "TARGET_RA": 180.0,
            "TARGET_DEC": 10.0,
            "Z": 1.23,
            "SPECTYPE": "QSO",
            "ZWARN": 0,
        },
        {
            "TARGETID": 39628,
            "TARGET_RA": 181.0,
            "TARGET_DEC": 11.0,
            "Z": 0.5,
            "SPECTYPE": "GALAXY",
            "ZWARN": 0,
        },
    ]
    objects = desi.normalize_desi_rows(rows, provenance=_PROV)
    assert objects[0].uid == "desi:39627"
    assert objects[0].source == "DESI"
    assert objects[0].object_type is ObjectType.QUASAR
    assert objects[0].redshift == 1.23
    assert objects[0].metadata["spectype"] == "QSO"
    assert objects[0].metadata["zwarn"] == "0"
    assert objects[1].object_type is ObjectType.GALAXY


@pytest.mark.parametrize(
    "spectype,expected",
    [
        ("GALAXY", ObjectType.GALAXY),
        ("QSO", ObjectType.QUASAR),
        ("STAR", ObjectType.STAR),
        ("other", ObjectType.UNKNOWN),
        (None, ObjectType.UNKNOWN),
    ],
)
def test_spectype_mapping(spectype, expected) -> None:
    row = {"TARGETID": 1, "TARGET_RA": 10.0, "TARGET_DEC": 10.0, "Z": 0.3}
    if spectype is not None:
        row["SPECTYPE"] = spectype
    assert desi.normalize_desi_rows([row], provenance=_PROV)[0].object_type is expected


def test_missing_targetid_is_malformed() -> None:
    with pytest.raises(MalformedResponseError):
        desi.normalize_desi_rows([{"TARGET_RA": 1.0, "TARGET_DEC": 1.0}], provenance=_PROV)


def test_missing_radec_is_malformed() -> None:
    with pytest.raises(MalformedResponseError):
        desi.normalize_desi_rows([{"TARGETID": 1, "Z": 0.3}], provenance=_PROV)


# --- region fetch is intentionally not enabled ---


def test_fetch_region_not_supported() -> None:
    with pytest.raises(ConnectorNotSupportedError) as excinfo:
        desi.fetch_desi_region(180.0, 10.0, 0.1)
    message = str(excinfo.value)
    assert "load_desi_file" in message
    assert "Astro Data Lab" in message


# --- local-file import pathway ---


def _write_desi_ecsv(path) -> None:
    table = Table()
    table["TARGETID"] = np.array([1001, 1002], dtype="int64")
    table["TARGET_RA"] = [200.0, 201.0]
    table["TARGET_DEC"] = [-5.0, -6.0]
    table["Z"] = [0.8, 3.2]
    table["SPECTYPE"] = ["GALAXY", "QSO"]
    table["ZWARN"] = np.array([0, 0], dtype="int32")
    table.write(str(path))


def test_load_desi_file(tmp_path) -> None:
    path = tmp_path / "desi_zcat.ecsv"
    _write_desi_ecsv(path)
    objects = desi.load_desi_file(path)
    assert [o.uid for o in objects] == ["desi:1001", "desi:1002"]
    assert {o.object_type for o in objects} == {ObjectType.GALAXY, ObjectType.QUASAR}
    assert objects[0].provenance is not None
    assert objects[0].provenance.endpoint.endswith("desi_zcat.ecsv")


def test_load_desi_file_missing(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        desi.load_desi_file(tmp_path / "nope.ecsv")


def test_load_desi_file_empty(tmp_path) -> None:
    path = tmp_path / "empty.ecsv"
    table = Table()
    table["TARGETID"] = np.array([], dtype="int64")
    table["TARGET_RA"] = np.array([], dtype="float64")
    table["TARGET_DEC"] = np.array([], dtype="float64")
    table.write(str(path))
    with pytest.raises(EmptyResultError):
        desi.load_desi_file(path)
