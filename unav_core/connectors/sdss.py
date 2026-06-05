"""SDSS connector: a regional query via ``astroquery.sdss`` + row normalisation.

Fetches SDSS objects in a small sky region and normalises them to UNAV
:class:`~unav_core.data.schema.CatalogObject` records.

**Redshift handling (important):** in *spectroscopic* mode SDSS returns a ``z``
column that is the **redshift**; in *photometric* mode ``z`` is the **z-band
magnitude**. UNAV-SA only treats ``z`` as a redshift when ``spectro=True`` — it
will never mistake a band magnitude for a cosmological redshift. See
``docs/SDSS_CONNECTOR.md`` and ``docs/EXTRAGALACTIC_DATA_LIMITATIONS.md``.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from unav_core.connectors.base import (
    ConnectorError,
    ConnectorNetworkError,
    EmptyResultError,
    MalformedResponseError,
    enforce_limit,
    enforce_radius,
    extract_rows,
    field,
    require_astroquery,
    to_float,
)
from unav_core.data.object_types import ObjectType
from unav_core.data.schema import CatalogObject
from unav_core.provenance.provenance import Provenance

#: Conservative default cone radius (deg) ~ 3 arcmin.
DEFAULT_SDSS_RADIUS_DEG = 0.05

#: Default row cap.
DEFAULT_SDSS_LIMIT = 500

#: SDSS data release used by default.
DEFAULT_DATA_RELEASE = 17

_SPECTRO_FIELDS = ("specobjid", "ra", "dec", "z", "class", "subclass")
_PHOTO_FIELDS = ("objid", "ra", "dec", "type", "modelMag_r")
_MAGNITUDE_FIELDS = ("modelMag_r", "cModelMag_r", "petroMag_r", "psfMag_r", "fiberMag_r", "r")

_CLASS_TO_TYPE = {
    "STAR": ObjectType.STAR,
    "GALAXY": ObjectType.GALAXY,
    "QSO": ObjectType.QUASAR,
    "QUASAR": ObjectType.QUASAR,
    # SDSS photometric "type" codes:
    "3": ObjectType.GALAXY,
    "6": ObjectType.STAR,
}


def fetch_sdss_region(
    ra_deg: float,
    dec_deg: float,
    radius_deg: float = DEFAULT_SDSS_RADIUS_DEG,
    limit: int = DEFAULT_SDSS_LIMIT,
    *,
    spectro: bool = True,
    data_release: int = DEFAULT_DATA_RELEASE,
    allow_large_radius: bool = False,
) -> list[CatalogObject]:
    """Cone-search SDSS and return normalised ``CatalogObject`` records.

    With ``spectro=True`` (default) results carry a class and a redshift; with
    ``spectro=False`` only positions and an r-band magnitude are reliable.
    """
    enforce_radius(radius_deg, allow_large=allow_large_radius)
    enforce_limit(limit)

    sdss = require_astroquery("astroquery.sdss").SDSS
    coordinates, radius = _coords_and_radius(ra_deg, dec_deg, radius_deg)
    fields = (
        {"specobj_fields": list(_SPECTRO_FIELDS)}
        if spectro
        else {"photoobj_fields": list(_PHOTO_FIELDS)}
    )
    try:
        table = sdss.query_region(
            coordinates, radius=radius, spectro=spectro, data_release=data_release, **fields
        )
    except ConnectorError:
        raise
    except Exception as exc:  # noqa: BLE001 - any remote failure is a network error
        raise ConnectorNetworkError(f"SDSS query failed: {exc}") from exc

    if table is None:
        raise EmptyResultError(
            f"SDSS returned no objects for region ra={ra_deg}, dec={dec_deg}, r={radius_deg} deg"
        )
    rows = extract_rows(table)
    if not rows:
        raise EmptyResultError(
            f"SDSS returned no objects for region ra={ra_deg}, dec={dec_deg}, r={radius_deg} deg"
        )
    rows = rows[:limit]  # enforce the row cap locally (regional, limited)

    provenance = _sdss_provenance(ra_deg, dec_deg, radius_deg, limit, spectro, data_release)
    return normalize_sdss_rows(rows, provenance=provenance, spectro=spectro)


def normalize_sdss_rows(
    rows: list[dict[str, Any]], *, provenance: Provenance, spectro: bool = True
) -> list[CatalogObject]:
    """Normalise SDSS result rows into ``CatalogObject`` records."""
    return [_normalize_sdss_row(row, provenance, spectro) for row in rows]


def _normalize_sdss_row(
    row: dict[str, Any], provenance: Provenance, spectro: bool
) -> CatalogObject:
    identifier = field(row, "specobjid")
    if identifier is None:
        identifier = field(row, "objid")
    if identifier is None:
        raise MalformedResponseError(f"SDSS row missing specobjid/objid: {row!r}")

    ra = to_float(field(row, "ra"))
    dec = to_float(field(row, "dec"))
    if ra is None or dec is None:
        raise MalformedResponseError(f"SDSS row missing ra/dec: {row!r}")

    # Only spectroscopic 'z' is a redshift; photometric 'z' is a band magnitude.
    redshift = to_float(field(row, "z", "redshift")) if spectro else None

    class_value = field(row, "class")
    if class_value is None:
        class_value = field(row, "type")
    object_type = _sdss_object_type(class_value)

    identifier_str = _id_to_str(identifier)
    metadata: dict[str, Any] = {"sdss_id": identifier_str}
    if class_value is not None:
        metadata["sdss_class"] = str(class_value)
    subclass = field(row, "subclass")
    if subclass:
        metadata["sdss_subclass"] = str(subclass)

    try:
        return CatalogObject(
            uid=f"sdss:{identifier_str}",
            source="SDSS",
            object_type=object_type,
            name=f"SDSS {identifier_str}",
            ra_deg=ra,
            dec_deg=dec,
            redshift=redshift,
            apparent_magnitude=_first_magnitude(row),
            metadata=metadata,
            provenance=provenance,
        )
    except ValidationError as exc:
        raise MalformedResponseError(f"SDSS row failed schema validation: {exc}") from exc


def _sdss_object_type(value: Any) -> ObjectType:
    if value is None:
        return ObjectType.UNKNOWN
    return _CLASS_TO_TYPE.get(str(value).strip().upper(), ObjectType.UNKNOWN)


def _first_magnitude(row: dict[str, Any]) -> float | None:
    for key in _MAGNITUDE_FIELDS:
        value = to_float(field(row, key))
        if value is not None:
            return value
    return None


def _id_to_str(value: Any) -> str:
    try:
        return str(int(value))
    except (TypeError, ValueError):
        return str(value)


def _coords_and_radius(ra_deg: float, dec_deg: float, radius_deg: float):
    # Build the SkyCoord/radius lazily via the astro layer (keeps imports light).
    from unav_core.astro._backend import get_units
    from unav_core.astro.coordinates import skycoord_from_radec

    return skycoord_from_radec(ra_deg, dec_deg), radius_deg * get_units().deg


def _sdss_provenance(
    ra_deg: float,
    dec_deg: float,
    radius_deg: float,
    limit: int,
    spectro: bool,
    data_release: int,
) -> Provenance:
    return Provenance.now(
        "SDSS",
        catalog=f"SDSS DR{data_release}",
        reference_frame="ICRS",
        endpoint="astroquery.sdss",
        query_parameters={
            "ra_deg": float(ra_deg),
            "dec_deg": float(dec_deg),
            "radius_deg": float(radius_deg),
            "limit": int(limit),
            "spectro": bool(spectro),
            "data_release": int(data_release),
        },
    )
