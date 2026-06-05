"""Deterministic synthetic catalog generator for tests and offline development.

Produces tiny, reproducible sample catalogs (no network, no external data) made
of nearby stars, galaxies, quasars, solar-system placeholder bodies and custom
objects. The same ``seed`` always yields the same catalog: generation uses only
the standard-library RNG and attaches **no** wall-clock timestamps.

The generator builds objects in the pure data layer, then routes **all**
coordinate maths through ``unav_core.astro`` (Astropy): by default it fills the
ICRS Cartesian ``x/y/z`` (parsecs) of every object that has a usable distance via
:func:`unav_core.astro.enrich.enrich_object_coordinates`. Astropy is imported
**lazily** — only when generating, and only when ``enrich=True`` — so importing
this module stays cheap and free of any ``unav_core.astro`` / ``unav_core.db`` /
network dependency. Pass ``enrich=False`` for sky-only objects (no ``x/y/z``).

See ``docs/SAMPLE_DATA.md`` and ``docs/COORDINATE_PIPELINE.md``.
"""

from __future__ import annotations

import random

from unav_core.data.io import write_jsonl
from unav_core.data.object_types import ObjectType
from unav_core.data.schema import CANONICAL_UNITS, CatalogObject
from unav_core.provenance.provenance import Provenance

#: Identifies this generator in provenance/metadata.
GENERATOR_NAME = "unav_core.data.sample_generator"

#: Default number of objects to generate.
DEFAULT_COUNT = 100

#: Hard upper bound on the number of objects (task constraint).
MAX_COUNT = 5000

#: Reference frame and epoch the synthetic ICRS positions are stamped with.
_REFERENCE_FRAME = "ICRS"
_REFERENCE_EPOCH = "J2000.0"

#: 1 astronomical unit expressed in parsecs (IAU-defined factor).
_AU_IN_PC = 4.84813681e-6

#: Relative proportions of each category in a generated catalog.
_CATEGORY_WEIGHTS: dict[str, int] = {
    "star": 50,
    "galaxy": 25,
    "quasar": 10,
    "solar": 10,
    "custom": 5,
}

#: Generation order (stable, for determinism).
_CATEGORY_ORDER: tuple[str, ...] = ("star", "galaxy", "quasar", "solar", "custom")

#: Synthetic, clearly-non-real source label per category.
_SOURCE: dict[str, str] = {
    "star": "sample-gaia",
    "galaxy": "sample-sdss",
    "quasar": "sample-sdss",
    "solar": "sample-jpl",
    "custom": "sample-custom",
}

_SOLAR_SUBTYPES: tuple[ObjectType, ...] = (
    ObjectType.PLANET,
    ObjectType.MOON,
    ObjectType.ASTEROID,
    ObjectType.COMET,
)
_SOLAR_CODE: dict[ObjectType, str] = {
    ObjectType.PLANET: "PLAN",
    ObjectType.MOON: "MOON",
    ObjectType.ASTEROID: "AST",
    ObjectType.COMET: "COM",
}


def generate_sample_catalog(
    count: int = DEFAULT_COUNT, *, seed: int = 0, enrich: bool = True
) -> list[CatalogObject]:
    """Generate a deterministic list of ``count`` synthetic ``CatalogObject``.

    The same ``(count, seed)`` always produces the same objects. ``count`` must
    be in ``[0, MAX_COUNT]``.

    When ``enrich`` is true (the default), every object with a usable distance
    gets its ICRS Cartesian ``x/y/z`` (parsecs) computed through the
    Astropy-backed :func:`unav_core.astro.enrich.enrich_object_coordinates`.
    Objects carrying only a redshift (galaxies, quasars) keep ``x/y/z`` unset.
    Pass ``enrich=False`` to get sky-only objects (no Cartesian positions).
    """
    if count < 0:
        raise ValueError("count must be >= 0")
    if count > MAX_COUNT:
        raise ValueError(f"count must be <= {MAX_COUNT}")

    rng = random.Random(seed)
    allocation = _allocate(count)
    provenance = {source: _provenance(source, seed) for source in set(_SOURCE.values())}

    builders = {
        "star": _make_star,
        "galaxy": _make_galaxy,
        "quasar": _make_quasar,
        "solar": _make_solar,
        "custom": _make_custom,
    }

    objects: list[CatalogObject] = []
    global_index = 0
    for category in _CATEGORY_ORDER:
        for type_index in range(1, allocation[category] + 1):
            global_index += 1
            objects.append(builders[category](rng, global_index, type_index, provenance))

    if enrich:
        objects = _enrich_cartesian(objects)
    return objects


def write_sample_catalog(
    path, count: int = DEFAULT_COUNT, *, seed: int = 0, enrich: bool = True
) -> int:
    """Generate a sample catalog and write it as JSONL. Returns the count written."""
    return write_jsonl(generate_sample_catalog(count, seed=seed, enrich=enrich), path)


def _enrich_cartesian(objects: list[CatalogObject]) -> list[CatalogObject]:
    """Fill ICRS Cartesian ``x/y/z`` via the Astropy-backed astro layer.

    The import is local so that importing this module (and the pure data layer)
    never pulls in Astropy; it happens only when coordinates are computed.
    """
    from unav_core.astro.enrich import enrich_object_coordinates

    return [enrich_object_coordinates(obj) for obj in objects]


def _allocate(count: int) -> dict[str, int]:
    total_weight = sum(_CATEGORY_WEIGHTS.values())
    allocation = {cat: count * weight // total_weight for cat, weight in _CATEGORY_WEIGHTS.items()}

    # Hand out the rounding remainder by descending weight (then name) for stability.
    remainder = count - sum(allocation.values())
    for cat in sorted(_CATEGORY_WEIGHTS, key=lambda c: (-_CATEGORY_WEIGHTS[c], c)):
        if remainder <= 0:
            break
        allocation[cat] += 1
        remainder -= 1

    # When there is room, guarantee at least one object of every category.
    if count >= len(_CATEGORY_WEIGHTS):
        for cat in _CATEGORY_ORDER:
            if allocation[cat] == 0:
                donor = max(allocation, key=lambda c: allocation[c])
                allocation[donor] -= 1
                allocation[cat] += 1
    return allocation


def _provenance(source: str, seed: int) -> Provenance:
    # No retrieved_at: keeps generation deterministic and honest (no real fetch).
    # The coordinate system (reference_frame + epoch) and the unit convention are
    # recorded so downstream layers can interpret ra/dec/distance and x/y/z.
    return Provenance(
        source=source,
        catalog="unav-sample",
        version="v1",
        reference_frame=_REFERENCE_FRAME,
        epoch=_REFERENCE_EPOCH,
        query_parameters={"seed": seed, "generator": GENERATOR_NAME},
        units=dict(CANONICAL_UNITS),
        notes="synthetic sample data; not from a real survey",
    )


def _radec(rng: random.Random) -> tuple[float, float]:
    ra = rng.uniform(0.0, 360.0) % 360.0  # keep strictly within [0, 360)
    dec = rng.uniform(-90.0, 90.0)
    return round(ra, 6), round(dec, 6)


def _make_star(
    rng: random.Random, gidx: int, tidx: int, prov: dict[str, Provenance]
) -> CatalogObject:
    ra, dec = _radec(rng)
    distance_pc = round(rng.uniform(1.0, 500.0), 4)
    parallax_mas = round(1000.0 / distance_pc, 4)
    apparent_magnitude = round(rng.uniform(-1.0, 15.0), 3)
    return CatalogObject(
        uid=f"SAMPLE-{gidx:05d}-STAR",
        source=_SOURCE["star"],
        object_type=ObjectType.STAR,
        name=f"Sample Star {tidx}",
        ra_deg=ra,
        dec_deg=dec,
        distance_pc=distance_pc,
        parallax_mas=parallax_mas,
        apparent_magnitude=apparent_magnitude,
        metadata={"sample": True, "category": "nearby_star"},
        provenance=prov[_SOURCE["star"]],
    )


def _make_galaxy(
    rng: random.Random, gidx: int, tidx: int, prov: dict[str, Provenance]
) -> CatalogObject:
    ra, dec = _radec(rng)
    redshift = round(rng.uniform(0.001, 0.2), 6)
    apparent_magnitude = round(rng.uniform(8.0, 20.0), 3)
    return CatalogObject(
        uid=f"SAMPLE-{gidx:05d}-GAL",
        source=_SOURCE["galaxy"],
        object_type=ObjectType.GALAXY,
        name=f"Sample Galaxy {tidx}",
        ra_deg=ra,
        dec_deg=dec,
        redshift=redshift,
        apparent_magnitude=apparent_magnitude,
        metadata={"sample": True, "category": "galaxy"},
        provenance=prov[_SOURCE["galaxy"]],
    )


def _make_quasar(
    rng: random.Random, gidx: int, tidx: int, prov: dict[str, Provenance]
) -> CatalogObject:
    ra, dec = _radec(rng)
    redshift = round(rng.uniform(0.1, 6.0), 6)
    apparent_magnitude = round(rng.uniform(15.0, 25.0), 3)
    return CatalogObject(
        uid=f"SAMPLE-{gidx:05d}-QSO",
        source=_SOURCE["quasar"],
        object_type=ObjectType.QUASAR,
        name=f"Sample Quasar {tidx}",
        ra_deg=ra,
        dec_deg=dec,
        redshift=redshift,
        apparent_magnitude=apparent_magnitude,
        metadata={"sample": True, "category": "quasar"},
        provenance=prov[_SOURCE["quasar"]],
    )


def _make_solar(
    rng: random.Random, gidx: int, tidx: int, prov: dict[str, Provenance]
) -> CatalogObject:
    subtype = _SOLAR_SUBTYPES[(tidx - 1) % len(_SOLAR_SUBTYPES)]
    ra, dec = _radec(rng)
    distance_au = round(rng.uniform(0.3, 50.0), 4)
    distance_pc = round(distance_au * _AU_IN_PC, 12)
    apparent_magnitude = round(rng.uniform(-2.0, 20.0), 3)
    return CatalogObject(
        uid=f"SAMPLE-{gidx:05d}-{_SOLAR_CODE[subtype]}",
        source=_SOURCE["solar"],
        object_type=subtype,
        name=f"Sample {subtype.value.capitalize()} {tidx}",
        ra_deg=ra,
        dec_deg=dec,
        distance_pc=distance_pc,
        apparent_magnitude=apparent_magnitude,
        metadata={"sample": True, "category": "solar_system", "distance_au": distance_au},
        provenance=prov[_SOURCE["solar"]],
    )


def _make_custom(
    rng: random.Random, gidx: int, tidx: int, prov: dict[str, Provenance]
) -> CatalogObject:
    ra, dec = _radec(rng)
    distance_pc = round(rng.uniform(10.0, 1000.0), 4)
    tag = rng.choice(["alpha", "beta", "gamma", "delta"])
    return CatalogObject(
        uid=f"SAMPLE-{gidx:05d}-CUST",
        source=_SOURCE["custom"],
        object_type=ObjectType.CUSTOM,
        name=f"Custom Object {tidx}",
        ra_deg=ra,
        dec_deg=dec,
        distance_pc=distance_pc,
        metadata={"sample": True, "category": "custom", "tag": tag},
        provenance=prov[_SOURCE["custom"]],
    )
