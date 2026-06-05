# UNAV-SA — Sample Data

Tiny, **deterministic**, fully **offline** sample catalogs for exercising the
app and the database without any external network access. Implemented in
`unav_core.data.sample_generator`.

> Phase 4 scope. The generator builds objects with only the standard-library
> RNG, then routes coordinate maths through `unav_core.astro` (Astropy) to fill
> Cartesian `x/y/z`. Astropy is imported **lazily** (only when generating, only
> when `enrich=True`), so importing the module stays cheap and free of any
> `unav_core.astro` / `unav_core.db` / network dependency. See
> [`COORDINATE_PIPELINE.md`](COORDINATE_PIPELINE.md).

## What it generates

A mix of object types so queries and views have variety:

| Category | `ObjectType` | Has | Source label |
| --- | --- | --- | --- |
| Nearby stars | `star` | distance (pc) + parallax + magnitude | `sample-gaia` |
| Galaxies | `galaxy` | redshift + magnitude | `sample-sdss` |
| Quasars | `quasar` | redshift + magnitude | `sample-sdss` |
| Solar-system placeholders | `planet`/`moon`/`asteroid`/`comet` | distance (pc, from AU) + magnitude | `sample-jpl` |
| Custom objects | `custom` | distance (pc) | `sample-custom` |

Default proportions are 50/25/10/10/5 %; every category is guaranteed at least
one object when `count ≥ 5`. Source labels are deliberately `sample-…` prefixed
so synthetic data is never mistaken for a real survey.

Every generated object includes a valid `uid`, `source`, `object_type`, `name`,
`ra_deg`/`dec_deg`, a distance **or** redshift as appropriate for its type,
`metadata` (with `sample: true` and a `category`), and a `provenance` record
(carrying `reference_frame="ICRS"`, `epoch="J2000.0"` and the `CANONICAL_UNITS`).

By default the generator fills ICRS Cartesian `x/y/z` (parsecs) for every object
with a usable distance — stars, solar-system bodies and custom objects — by
calling the Astropy-backed `enrich_object_coordinates`. Redshift-only objects
(galaxies, quasars) stay sky-only (`x/y/z` unset; a redshift is not turned into a
Euclidean distance). Pass `--no-enrich` for sky-only objects.

## Determinism

The same `(count, seed)` always produces the **same** catalog, byte-for-byte:

- generation draws only from `random.Random(seed)` in a fixed order;
- provenance carries the `seed` but **no** wall-clock `retrieved_at`.

```python
from unav_core.data import generate_sample_catalog
a = generate_sample_catalog(100, seed=42)
b = generate_sample_catalog(100, seed=42)
assert [o.model_dump() for o in a] == [o.model_dump() for o in b]
```

## Sizing

- Default: **100** objects.
- Maximum: **5000** (`generate_sample_catalog` raises `ValueError` above it; the
  CLI caps `--count` at 5000).

## CLI

```bash
python tools/generate_sample_catalog.py \
    --count 100 --seed 42 --output samples/sample_catalog.jsonl
```

`samples/sample_catalog.jsonl` is generated with `--count 100 --seed 42` (65 of
the 100 objects carry `x/y/z`; the 35 redshift-only galaxies/quasars do not).
Add `--no-enrich` to omit the Cartesian positions.

## Use with the database

The generated catalog imports straight into the local cache (see
[`LOCAL_DATABASE.md`](LOCAL_DATABASE.md)):

```bash
python tools/import_catalog.py \
    --input samples/sample_catalog.jsonl --db data/unav.db \
    --dataset-name sample --enrich        # --enrich fills x/y/z for 3D queries
```

`--enrich` on import is **idempotent**: objects already carrying `x/y/z` (as the
default sample does) pass through unchanged, while any without are enriched.

## Programmatic API

```python
from unav_core.data import generate_sample_catalog, write_sample_catalog

objects = generate_sample_catalog(count=100, seed=42)   # list[CatalogObject], x/y/z filled
sky_only = generate_sample_catalog(count=100, seed=42, enrich=False)  # no x/y/z
write_sample_catalog("samples/sample_catalog.jsonl", count=100, seed=42)
```
