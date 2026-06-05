"""NASA/JPL Horizons connector: per-body ephemerides via ``astroquery.jplhorizons``.

Fetches the sky position (and range) of solar-system bodies at a given **static
epoch** and normalises them to UNAV
:class:`~unav_core.data.schema.CatalogObject` records, including ICRS Cartesian
``x/y/z`` (parsecs) so the bodies can be viewed in 3D. Well-known body names are
classified (planet/moon) so the UI colours them distinctly.

See ``docs/JPL_SOLAR_SYSTEM_WORKFLOW.md``, ``docs/EPOCH_OBJECTS.md``,
``docs/JPL_CONNECTOR.md`` and ``docs/DATA_FETCHING_SAFETY.md``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import ValidationError

from unav_core.connectors.base import (
    AU_IN_PC,
    ConnectorError,
    ConnectorNetworkError,
    EmptyResultError,
    MalformedResponseError,
    extract_rows,
    require_astroquery,
    to_float,
)
from unav_core.data.object_types import ObjectType
from unav_core.data.schema import CatalogObject
from unav_core.provenance.provenance import Provenance

#: Default observer location (Horizons code). "@sun" = heliocentric.
DEFAULT_CENTER = "@sun"

#: Well-known body names -> object type (so the UI colours them distinctly).
#: Numeric Horizons ids (e.g. "499") are not classified here -> ``UNKNOWN``.
_PLANET_NAMES = frozenset(
    {"mercury", "venus", "earth", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto"}
)
_MOON_NAMES = frozenset({"moon", "luna"})


def classify_body(name: str) -> ObjectType:
    """Classify a solar-system body by **name** (planet/moon), else ``UNKNOWN``.

    Matching is case-insensitive. Pluto is grouped with the planets for display.
    Numeric Horizons ids are not classified (use an explicit type for those).
    """
    key = str(name).strip().lower()
    if key in _PLANET_NAMES:
        return ObjectType.PLANET
    if key in _MOON_NAMES:
        return ObjectType.MOON
    return ObjectType.UNKNOWN


def fetch_jpl_body(
    body: str,
    epoch: str | float,
    center: str = DEFAULT_CENTER,
    *,
    object_type: ObjectType | str = ObjectType.UNKNOWN,
) -> CatalogObject:
    """Fetch one body's ephemeris at ``epoch`` and normalise it.

    ``epoch`` is a Julian Date (number or numeric string) or an ISO-8601 time;
    ``center`` is a Horizons observer/location code; ``object_type`` classifies
    the body (planet/moon/asteroid/comet/unknown).
    """
    horizons_cls = require_astroquery("astroquery.jplhorizons").Horizons
    jd = _epoch_to_jd(epoch)
    try:
        query = horizons_cls(id=str(body), location=str(center), epochs=jd)
        ephemerides = query.ephemerides()
    except ConnectorError:
        raise
    except Exception as exc:  # noqa: BLE001 - any remote failure is a network error
        raise ConnectorNetworkError(f"JPL Horizons query failed for {body!r}: {exc}") from exc

    rows = extract_rows(ephemerides)
    if not rows:
        raise EmptyResultError(
            f"JPL Horizons returned no ephemeris for {body!r} at epoch {epoch!r}"
        )
    return _normalize_jpl_row(
        rows[0], body=body, epoch=epoch, center=center, object_type=object_type
    )


def fetch_jpl_solar_system(
    bodies: Mapping[str, ObjectType | str] | Sequence[str],
    epoch: str | float,
    center: str = DEFAULT_CENTER,
) -> list[CatalogObject]:
    """Fetch several bodies at one epoch.

    ``bodies`` may be a sequence of names (typed ``unknown``) or a mapping of
    ``{name: object_type}``.
    """
    return [
        fetch_jpl_body(body, epoch, center, object_type=object_type)
        for body, object_type in _normalize_bodies(bodies)
    ]


def _normalize_bodies(
    bodies: Mapping[str, ObjectType | str] | Sequence[str],
) -> list[tuple[str, ObjectType]]:
    if isinstance(bodies, Mapping):
        return [(str(name), ObjectType.coerce(otype)) for name, otype in bodies.items()]
    if isinstance(bodies, Sequence) and not isinstance(bodies, (str, bytes)):
        # A bare list of names is classified by name (planets/moons), else unknown.
        return [(str(name), classify_body(name)) for name in bodies]
    raise TypeError("bodies must be a sequence of names or a mapping {name: object_type}")


def _normalize_jpl_row(
    row: dict[str, Any],
    *,
    body: str,
    epoch: str | float,
    center: str,
    object_type: ObjectType | str,
) -> CatalogObject:
    ra = to_float(row.get("RA"))
    dec = to_float(row.get("DEC"))
    if ra is None or dec is None:
        raise MalformedResponseError(f"JPL row missing RA/DEC for {body!r}: {row!r}")

    delta_au = to_float(row.get("delta"))
    distance_pc = round(delta_au * AU_IN_PC, 12) if delta_au is not None and delta_au >= 0 else None
    targetname = row.get("targetname")
    name = str(targetname) if targetname else str(body)

    metadata: dict[str, Any] = {"body": str(body), "center": str(center), "epoch": str(epoch)}
    if delta_au is not None:
        metadata["distance_au"] = delta_au
    if targetname:
        metadata["targetname"] = str(targetname)

    try:
        obj = CatalogObject(
            uid=f"jpl:{body}:{epoch}",
            source="JPL Horizons",
            object_type=ObjectType.coerce(object_type),
            name=name,
            ra_deg=ra,
            dec_deg=dec,
            distance_pc=distance_pc,
            apparent_magnitude=to_float(row.get("V")),
            metadata=metadata,
            provenance=Provenance.now(
                "JPL Horizons",
                catalog="JPL Horizons",
                reference_frame="ICRS",
                epoch=str(epoch),
                endpoint="astroquery.jplhorizons",
                query_parameters={"body": str(body), "epoch": str(epoch), "center": str(center)},
            ),
        )
    except ValidationError as exc:
        raise MalformedResponseError(f"JPL row failed schema validation: {exc}") from exc

    # Compute ICRS Cartesian x/y/z (parsecs) so the body is viewable in 3D.
    # Solar-system distances are AU-scale, so x/y/z are tiny in parsecs (see
    # docs/EPOCH_OBJECTS.md); a JPL-only 3D view auto-frames to that scale.
    from unav_core.astro.enrich import enrich_object_coordinates

    return enrich_object_coordinates(obj)


def _epoch_to_jd(epoch: str | float) -> float:
    if isinstance(epoch, (int, float)):
        return float(epoch)
    text = str(epoch).strip()
    try:
        return float(text)  # already a Julian Date
    except ValueError:
        pass
    # ISO-8601 string -> JD (Astropy; astroquery already depends on Astropy).
    from unav_core.astro.time import iso_to_julian_date

    return iso_to_julian_date(text)
