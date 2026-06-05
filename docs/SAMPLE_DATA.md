# UNAV-SA — Sample Data

Tiny, **deterministic**, fully **offline** sample catalogs for exercising the
app and the database without any external network access. Implemented in
`unav_core.data.sample_generator`.

> Phase 4 scope. The generator lives in the pure data layer — it depends on
> nothing in `unav_core.astro`, `unav_core.db`, or any network. It uses only the
> standard-library RNG.

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
`metadata` (with `sample: true` and a `category`), and a `provenance` record.

Cartesian `x/y/z` are **not** set by the generator (that would require Astropy).
Compute them at import time with `--enrich` (see below).

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

`samples/sample_catalog.jsonl` is generated with `--count 100 --seed 42`.

## Use with the database

The generated catalog imports straight into the local cache (see
[`LOCAL_DATABASE.md`](LOCAL_DATABASE.md)):

```bash
python tools/import_catalog.py \
    --input samples/sample_catalog.jsonl --db data/unav.db \
    --dataset-name sample --enrich        # --enrich fills x/y/z for 3D queries
```

## Programmatic API

```python
from unav_core.data import generate_sample_catalog, write_sample_catalog

objects = generate_sample_catalog(count=100, seed=42)   # list[CatalogObject]
write_sample_catalog("samples/sample_catalog.jsonl", count=100, seed=42)
```
