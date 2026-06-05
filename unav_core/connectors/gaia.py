"""Gaia DR3 connector: a regional, limited cone search via ``astroquery.gaia``.

Fetches stars in a small sky region and normalises them to UNAV
:class:`~unav_core.data.schema.CatalogObject` records. Raw Gaia fields are mapped
(positions, parallax, photometry, proper motion, radial velocity) and a
``distance_pc`` is derived from a **positive** parallax (``1000 / parallax_mas``).
The Cartesian ``x/y/z`` are left to the optional Astropy enrichment step
(``import ... --enrich``), so this connector needs no Astropy itself.

See ``docs/GAIA_WORKFLOW.md``, ``docs/GAIA_CONNECTOR.md`` and
``docs/DATA_FETCHING_SAFETY.md``.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from unav_core.connectors.base import (
    DEFAULT_GAIA_LIMIT,
    ConnectorError,
    ConnectorNetworkError,
    EmptyResultError,
    MalformedResponseError,
    enforce_limit,
    enforce_radius,
    extract_rows,
    require_astroquery,
    to_float,
)
from unav_core.data.object_types import ObjectType
from unav_core.data.schema import CatalogObject
from unav_core.provenance.provenance import Provenance

#: Gaia DR3 source table.
GAIA_TABLE = "gaiadr3.gaia_source"

#: Gaia DR3 reference epoch.
GAIA_EPOCH = "J2016.0"

_COLUMNS = (
    "source_id",
    "ra",
    "dec",
    "parallax",
    "phot_g_mean_mag",
    "bp_rp",
    "pmra",
    "pmdec",
    "radial_velocity",
)


def fetch_gaia_region(
    ra_deg: float,
    dec_deg: float,
    radius_deg: float,
    limit: int = DEFAULT_GAIA_LIMIT,
    *,
    allow_large_radius: bool = False,
) -> list[CatalogObject]:
    """Cone-search Gaia DR3 and return normalised ``CatalogObject`` stars.

    Regional and limited by design: ``radius_deg`` is capped (override with
    ``allow_large_radius``) and ``limit`` rows are requested server-side.
    """
    enforce_radius(radius_deg, allow_large=allow_large_radius)
    enforce_limit(limit)

    gaia = require_astroquery("astroquery.gaia").Gaia
    adql = build_gaia_adql(ra_deg, dec_deg, radius_deg, limit)
    try:
        job = gaia.launch_job(adql)
        results = job.get_results()
    except ConnectorError:
        raise
    except Exception as exc:  # noqa: BLE001 - any remote failure is a network error
        raise ConnectorNetworkError(f"Gaia query failed: {exc}") from exc

    rows = extract_rows(results)
    if not rows:
        raise EmptyResultError(
            f"Gaia returned no sources for region ra={ra_deg}, dec={dec_deg}, r={radius_deg} deg"
        )

    provenance = _gaia_provenance(ra_deg, dec_deg, radius_deg, limit, adql)
    return normalize_gaia_rows(rows, provenance=provenance)


def build_gaia_adql(ra_deg: float, dec_deg: float, radius_deg: float, limit: int) -> str:
    """Build the regional, row-capped ADQL cone query."""
    columns = ", ".join(_COLUMNS)
    return (
        f"SELECT TOP {int(limit)} {columns} FROM {GAIA_TABLE} "
        f"WHERE 1 = CONTAINS(POINT('ICRS', ra, dec), "
        f"CIRCLE('ICRS', {float(ra_deg)}, {float(dec_deg)}, {float(radius_deg)}))"
    )


def normalize_gaia_rows(
    rows: list[dict[str, Any]], *, provenance: Provenance
) -> list[CatalogObject]:
    """Normalise Gaia result rows into ``CatalogObject`` stars."""
    return [_normalize_gaia_row(row, provenance) for row in rows]


def _normalize_gaia_row(row: dict[str, Any], provenance: Provenance) -> CatalogObject:
    source_id = row.get("source_id")
    ra = to_float(row.get("ra"))
    dec = to_float(row.get("dec"))
    if source_id is None or ra is None or dec is None:
        raise MalformedResponseError(f"Gaia row missing source_id/ra/dec: {row!r}")
    try:
        gaia_id = int(source_id)
    except (TypeError, ValueError) as exc:
        raise MalformedResponseError(f"invalid Gaia source_id: {source_id!r}") from exc

    parallax_mas = to_float(row.get("parallax"))
    # Distance from a POSITIVE parallax only (1000 / parallax[mas]); Gaia's real
    # negative/zero parallaxes do not yield a distance. x/y/z come from --enrich.
    distance_pc = 1000.0 / parallax_mas if parallax_mas is not None and parallax_mas > 0.0 else None

    try:
        return CatalogObject(
            uid=f"gaia:{gaia_id}",
            native_id=str(gaia_id),
            source="Gaia DR3",
            object_type=ObjectType.STAR,
            name=f"Gaia DR3 {gaia_id}",
            ra_deg=ra,
            dec_deg=dec,
            parallax_mas=parallax_mas,
            distance_pc=distance_pc,
            apparent_magnitude=to_float(row.get("phot_g_mean_mag")),
            color_index=to_float(row.get("bp_rp")),
            proper_motion_ra_masyr=to_float(row.get("pmra")),
            proper_motion_dec_masyr=to_float(row.get("pmdec")),
            radial_velocity_kms=to_float(row.get("radial_velocity")),
            metadata={"gaia_source_id": gaia_id},
            provenance=provenance,
        )
    except ValidationError as exc:
        raise MalformedResponseError(f"Gaia row failed schema validation: {exc}") from exc


def _gaia_provenance(
    ra_deg: float, dec_deg: float, radius_deg: float, limit: int, adql: str
) -> Provenance:
    return Provenance.now(
        "Gaia DR3",
        catalog="Gaia DR3",
        version=GAIA_TABLE,
        reference_frame="ICRS",
        epoch=GAIA_EPOCH,
        endpoint="astroquery.gaia",
        query_parameters={
            "ra_deg": float(ra_deg),
            "dec_deg": float(dec_deg),
            "radius_deg": float(radius_deg),
            "limit": int(limit),
            "adql": adql,
        },
    )
