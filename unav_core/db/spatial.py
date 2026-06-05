"""Cone (spatial) search over the local cache.

A cone search is performed in two steps (see ``docs/SPATIAL_QUERY_STRATEGY.md``):

1. an **indexed bounding-box prefilter** in RA/Dec that selects candidate rows;
2. an **exact angular filter** (great-circle / haversine) applied in Python to
   the candidates.

The exact step uses a pure-Python haversine so the ``db`` layer carries no
Astropy dependency; ``angular_separation_deg`` is cross-checked against Astropy
in the tests.
"""

from __future__ import annotations

import math
from typing import Any

from sqlalchemy import and_, or_

from unav_core.data.schema import CatalogObject
from unav_core.db.database import Database
from unav_core.db.schema import objects_table


def angular_separation_deg(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    """Great-circle angular separation between two ICRS positions, in degrees."""
    phi1 = math.radians(dec1)
    phi2 = math.radians(dec2)
    dphi = phi2 - phi1
    dlambda = math.radians(ra2 - ra1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    a = min(1.0, max(0.0, a))
    return math.degrees(2.0 * math.asin(math.sqrt(a)))


def cone_search(
    db: Database,
    ra_deg: float,
    dec_deg: float,
    radius_deg: float,
    *,
    limit: int | None = None,
) -> list[CatalogObject]:
    """Return objects within ``radius_deg`` of ``(ra_deg, dec_deg)``, nearest first."""
    if radius_deg < 0.0:
        raise ValueError("radius_deg must be >= 0")

    candidates = db.fetch_objects(where=_bounding_box(ra_deg, dec_deg, radius_deg))
    tolerance = radius_deg + 1e-9

    scored: list[tuple[float, CatalogObject]] = []
    for obj in candidates:
        if obj.ra_deg is None or obj.dec_deg is None:
            continue
        separation = angular_separation_deg(ra_deg, dec_deg, obj.ra_deg, obj.dec_deg)
        if separation <= tolerance:
            scored.append((separation, obj))

    scored.sort(key=lambda item: item[0])
    objects = [obj for _, obj in scored]
    return objects[:limit] if limit is not None else objects


def _bounding_box(ra: float, dec: float, radius: float) -> Any:
    """Build the indexed RA/Dec bounding-box prefilter for a cone."""
    cols = objects_table.c
    dec_min = max(-90.0, dec - radius)
    dec_max = min(90.0, dec + radius)
    conditions = [
        cols.ra_deg.is_not(None),
        cols.dec_deg.is_not(None),
        cols.dec_deg >= dec_min,
        cols.dec_deg <= dec_max,
    ]

    cos_dec = math.cos(math.radians(dec))
    sin_radius = math.sin(math.radians(radius))
    # The cap reaches a pole -> the RA bound is meaningless; keep the full circle.
    if radius >= 90.0 or abs(dec) + radius >= 90.0 or cos_dec <= sin_radius:
        return and_(*conditions)

    # RA half-width of the cone's bounding box.
    delta_ra = math.degrees(math.asin(min(1.0, sin_radius / cos_dec)))
    ra_min = ra - delta_ra
    ra_max = ra + delta_ra
    if ra_min < 0.0 or ra_max >= 360.0:
        # Wrap across the 0/360 boundary.
        low = ra_min % 360.0
        high = ra_max % 360.0
        conditions.append(or_(cols.ra_deg >= low, cols.ra_deg <= high))
    else:
        conditions.append(and_(cols.ra_deg >= ra_min, cols.ra_deg <= ra_max))
    return and_(*conditions)
