"""DESI connector: a conservative foundation (normalisation + local file import).

DESI redshift catalogs are distributed as large files and via public services
(NOIRLab Astro Data Lab TAP, and SPARCL) — **not** as a casual cone-search API.
UNAV-SA therefore does **not** download DESI archives. This module provides:

* :func:`normalize_desi_rows` — map DESI redshift-catalog rows to ``CatalogObject``;
* :func:`load_desi_file` — import a DESI catalog **file you already have** locally;
* :func:`fetch_desi_region` — a documented placeholder that raises
  :class:`~unav_core.connectors.base.ConnectorNotSupportedError` with guidance
  toward the local-file pathway and the planned public-database workflow.

See ``docs/DESI_CONNECTOR.md`` and ``docs/EXTRAGALACTIC_DATA_LIMITATIONS.md``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from unav_core.connectors.base import (
    ConnectorNotSupportedError,
    EmptyResultError,
    MalformedResponseError,
    extract_rows,
    field,
    to_float,
)
from unav_core.data.object_types import ObjectType
from unav_core.data.schema import CatalogObject
from unav_core.provenance.provenance import Provenance

PathLike = str | Path

_SPECTYPE_TO_TYPE = {
    "GALAXY": ObjectType.GALAXY,
    "QSO": ObjectType.QUASAR,
    "QUASAR": ObjectType.QUASAR,
    "STAR": ObjectType.STAR,
}

_FETCH_GUIDANCE = (
    "Live DESI region fetching is intentionally not enabled in this foundation: "
    "DESI does not offer a casual cone-search download API and UNAV-SA never "
    "mirrors archives.\n"
    "Use load_desi_file(path) to import a DESI redshift catalog you have already "
    "downloaded locally, or normalize_desi_rows(...) for in-memory rows.\n"
    "The planned public-database workflow (NOIRLab Astro Data Lab TAP / SPARCL) "
    "is described in docs/DESI_CONNECTOR.md."
)


def fetch_desi_region(
    ra_deg: float,
    dec_deg: float,
    radius_deg: float,
    *,
    limit: int | None = None,
) -> list[CatalogObject]:
    """Not enabled: raises with guidance toward the local-file pathway.

    DESI cone-search downloading is out of scope for this conservative
    foundation (see the module docstring and ``docs/DESI_CONNECTOR.md``).
    """
    raise ConnectorNotSupportedError(_FETCH_GUIDANCE)


def load_desi_file(path: PathLike, *, limit: int | None = None) -> list[CatalogObject]:
    """Import a **local** DESI redshift-catalog file into ``CatalogObject`` records.

    Reads any table format Astropy understands (FITS, ECSV, CSV, VOTable) — the
    file must already exist locally; nothing is downloaded.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"DESI file not found: {file_path}")

    table = _read_table(file_path)
    rows = extract_rows(table)
    if limit is not None:
        rows = rows[:limit]
    if not rows:
        raise EmptyResultError(f"DESI file {file_path} contained no rows")

    provenance = _desi_file_provenance(file_path)
    return normalize_desi_rows(rows, provenance=provenance)


def normalize_desi_rows(
    rows: list[dict[str, Any]], *, provenance: Provenance
) -> list[CatalogObject]:
    """Normalise DESI redshift-catalog rows into ``CatalogObject`` records."""
    return [_normalize_desi_row(row, provenance) for row in rows]


def _normalize_desi_row(row: dict[str, Any], provenance: Provenance) -> CatalogObject:
    targetid = field(row, "TARGETID", "targetid")
    if targetid is None:
        raise MalformedResponseError(f"DESI row missing TARGETID: {row!r}")

    ra = to_float(field(row, "TARGET_RA", "ra", "RA"))
    dec = to_float(field(row, "TARGET_DEC", "dec", "DEC"))
    if ra is None or dec is None:
        raise MalformedResponseError(f"DESI row missing TARGET_RA/TARGET_DEC: {row!r}")

    redshift = to_float(field(row, "Z", "redshift"))
    spectype = field(row, "SPECTYPE", "spectype")
    object_type = _desi_object_type(spectype)
    targetid_str = _id_to_str(targetid)

    metadata: dict[str, Any] = {"desi_targetid": targetid_str}
    if spectype is not None:
        metadata["spectype"] = str(spectype).strip()
    zwarn = field(row, "ZWARN", "zwarn")
    if zwarn is not None:
        metadata["zwarn"] = _id_to_str(zwarn)

    try:
        return CatalogObject(
            uid=f"desi:{targetid_str}",
            source="DESI",
            object_type=object_type,
            name=f"DESI {targetid_str}",
            ra_deg=ra,
            dec_deg=dec,
            redshift=redshift,
            metadata=metadata,
            provenance=provenance,
        )
    except ValidationError as exc:
        raise MalformedResponseError(f"DESI row failed schema validation: {exc}") from exc


def _desi_object_type(value: Any) -> ObjectType:
    if value is None:
        return ObjectType.UNKNOWN
    return _SPECTYPE_TO_TYPE.get(str(value).strip().upper(), ObjectType.UNKNOWN)


def _id_to_str(value: Any) -> str:
    try:
        return str(int(value))
    except (TypeError, ValueError):
        return str(value)


def _read_table(file_path: Path):
    # Astropy is needed to read FITS/ECSV/CSV/VOTable; imported lazily.
    from astropy.table import Table

    try:
        return Table.read(str(file_path))
    except Exception as exc:  # noqa: BLE001 - surface any read/parse failure clearly
        raise MalformedResponseError(f"could not read DESI file {file_path}: {exc}") from exc


def _desi_file_provenance(file_path: Path) -> Provenance:
    return Provenance.now(
        "DESI",
        catalog="DESI",
        reference_frame="ICRS",
        endpoint=str(file_path),
        query_parameters={"file": str(file_path)},
        notes="imported from a local DESI catalog file (no download performed)",
    )
