"""Coordinate helpers backed by :class:`astropy.coordinates.SkyCoord`.

All sky positions are **ICRS** degrees (matching the canonical schema). The
Cartesian convention is the ICRS rectangular one Astropy produces:

* ``x`` toward (RA=0°, Dec=0°)
* ``y`` toward (RA=90°, Dec=0°)
* ``z`` toward the north celestial pole (Dec=+90°)

with the same length unit as the distance (parsecs throughout UNAV-SA). See
``docs/COORDINATE_CONVENTIONS.md``.

Requires Astropy — see :mod:`unav_core.astro._backend`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from unav_core.astro._backend import get_coordinates, get_units

if TYPE_CHECKING:
    from astropy.coordinates import SkyCoord


def skycoord_from_radec(
    ra_deg: float, dec_deg: float, distance_pc: float | None = None
) -> SkyCoord:
    """Build an ICRS :class:`~astropy.coordinates.SkyCoord` from RA/Dec (deg).

    If ``distance_pc`` is given the coordinate is 3D (carries a distance).
    """
    coord = get_coordinates()
    u = get_units()
    kwargs = {"ra": ra_deg * u.deg, "dec": dec_deg * u.deg, "frame": "icrs"}
    if distance_pc is not None:
        kwargs["distance"] = distance_pc * u.pc
    return coord.SkyCoord(**kwargs)


def radec_distance_to_cartesian(
    ra_deg: float, dec_deg: float, distance_pc: float
) -> tuple[float, float, float]:
    """Convert RA/Dec/distance to ICRS Cartesian ``(x, y, z)`` in parsecs."""
    cartesian = skycoord_from_radec(ra_deg, dec_deg, distance_pc).cartesian
    u = get_units()
    return (
        float(cartesian.x.to_value(u.pc)),
        float(cartesian.y.to_value(u.pc)),
        float(cartesian.z.to_value(u.pc)),
    )


def cartesian_to_radec_distance(x: float, y: float, z: float) -> tuple[float, float, float]:
    """Convert ICRS Cartesian ``(x, y, z)`` parsecs to ``(ra_deg, dec_deg, distance_pc)``."""
    coord = get_coordinates()
    u = get_units()
    representation = coord.CartesianRepresentation(x * u.pc, y * u.pc, z * u.pc)
    sky = coord.SkyCoord(representation, frame="icrs")
    return (
        float(sky.ra.to_value(u.deg)),
        float(sky.dec.to_value(u.deg)),
        float(sky.distance.to_value(u.pc)),
    )


def icrs_to_galactic(ra_deg: float, dec_deg: float) -> tuple[float, float]:
    """Convert ICRS RA/Dec (deg) to Galactic ``(l, b)`` in degrees."""
    galactic = skycoord_from_radec(ra_deg, dec_deg).galactic
    u = get_units()
    return (float(galactic.l.to_value(u.deg)), float(galactic.b.to_value(u.deg)))


def galactic_to_icrs(l_deg: float, b_deg: float) -> tuple[float, float]:
    """Convert Galactic ``(l, b)`` (deg) to ICRS ``(ra, dec)`` in degrees."""
    coord = get_coordinates()
    u = get_units()
    galactic = coord.SkyCoord(l=l_deg * u.deg, b=b_deg * u.deg, frame="galactic")
    icrs = galactic.icrs
    return (float(icrs.ra.to_value(u.deg)), float(icrs.dec.to_value(u.deg)))


def angular_separation(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    """Return the angular separation between two ICRS positions, in degrees."""
    first = skycoord_from_radec(ra1, dec1)
    second = skycoord_from_radec(ra2, dec2)
    u = get_units()
    return float(first.separation(second).to_value(u.deg))


#: Explicit ``_deg`` alias (the result is in degrees); same function, both names work.
angular_separation_deg = angular_separation
