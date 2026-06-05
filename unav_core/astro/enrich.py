"""Coordinate enrichment for :class:`~unav_core.data.schema.CatalogObject`.

This is the one place the astronomy layer bridges to the data layer: it takes a
catalog object and, when it has a usable sky position and distance, computes the
ICRS Cartesian ``x/y/z`` (parsecs). It is **functional** — it returns a new,
enriched object and never mutates the input.

Requires Astropy only when there is actually something to compute.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from unav_core.data.schema import CatalogObject


def enrich_object_coordinates(
    obj: CatalogObject,
    *,
    derive_distance_from_parallax: bool = True,
) -> CatalogObject:
    """Return a copy of ``obj`` with ``x/y/z`` filled from RA/Dec/distance.

    Behaviour:

    * If the object already has Cartesian ``x/y/z``, it is returned unchanged
      (existing values are never overwritten).
    * Otherwise, if it has both ``ra_deg`` and ``dec_deg`` and a usable
      distance, ``x/y/z`` are computed via
      :func:`~unav_core.astro.coordinates.radec_distance_to_cartesian`.
    * The distance is ``distance_pc`` when present. When it is absent and
      ``derive_distance_from_parallax`` is true, a **positive** parallax is
      inverted to a distance (``d[pc] = 1000 / parallax[mas]``) and stored on the
      returned object. Non-positive parallaxes are never inverted (they cannot
      yield a distance — see ``docs/PROVENANCE_AND_VALIDATION.md``).
    * If there is nothing to compute, the object is returned unchanged.

    Astropy is only imported/used when a position is actually computed.
    """
    if obj.has_cartesian:
        return obj
    if obj.ra_deg is None or obj.dec_deg is None:
        return obj

    updates: dict[str, float] = {}
    distance_pc = obj.distance_pc
    if distance_pc is None and derive_distance_from_parallax:
        if obj.parallax_mas is not None and obj.parallax_mas > 0.0:
            distance_pc = 1000.0 / obj.parallax_mas
            updates["distance_pc"] = distance_pc
    if distance_pc is None:
        return obj

    # Local import keeps the data layer free of an Astropy import dependency.
    from unav_core.astro.coordinates import radec_distance_to_cartesian

    x, y, z = radec_distance_to_cartesian(obj.ra_deg, obj.dec_deg, distance_pc)
    updates.update(x=x, y=y, z=z)
    return obj.model_copy(update=updates)
