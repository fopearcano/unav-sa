# UNAV-SA — Local Database

The local cache that stores normalized catalog objects for fast navigation
queries. Implemented in `unav_core.db` with **SQLAlchemy 2.x Core over SQLite**.

> Phase 3 scope. SQLite is the baseline engine. **DuckDB is not used**; it (or
> Postgres/PostGIS) may be added later as an *optional* backend behind the same
> `Database`/query API — see [`SPATIAL_QUERY_STRATEGY.md`](SPATIAL_QUERY_STRATEGY.md).

## Why SQLite + SQLAlchemy Core

- **SQLite** is zero-config, file-based, offline-friendly and ideal for a
  bounded local working set (per [`UNAV_SA_ARCHITECTURE.md`](UNAV_SA_ARCHITECTURE.md)).
- **SQLAlchemy Core** (not the ORM) keeps the SQL explicit while leaving room to
  swap the backend later. SQLAlchemy is already a core dependency.
- The `db` layer is **Astropy-free**: spatial filtering uses a pure-Python
  haversine, so importing `unav_core.db` never pulls Astropy.

## Tables

### `objects` (one row per catalog object)

`uid` (PK), `source`, `object_type`, `name`, `native_id`, `ra_deg`, `dec_deg`,
`distance_pc`, `parallax_mas`, `redshift`, `radial_velocity_kms`,
`proper_motion_ra_masyr`, `proper_motion_dec_masyr`, `apparent_magnitude`,
`absolute_magnitude`, `color_index`, `spectral_type`, `x`, `y`, `z`,
`provenance_json`.

> The table stores **every scalar field** of `CatalogObject` plus a per-object
> `provenance_json`, so a rehydrated object (and the inspector via
> `GET /objects/{uid}`) shows the full record — including provenance — for real
> connector data like Gaia. Free-form `metadata` lives in its own table.

### `metadata`

`uid` (PK), `metadata_json`. The object's `metadata` dict, stored only when
non-empty, joined back on read.

### `datasets`

`dataset_id` (PK), `name`, `source`, `object_count`, `created_at` (ISO-8601
UTC), `query_parameters_json`. One row per import/query.

### `provenance`

`dataset_id` (PK), `provenance_json`. Provenance is recorded at **dataset**
granularity (the batch's origin); **per-object** provenance is also persisted in
`objects.provenance_json` (so each object carries its own origin/audit record).

## Indexes

`source`, `object_type`, `(ra_deg, dec_deg)`, `x`, `y`, `z`, `distance_pc`,
`redshift`, `apparent_magnitude` — covering the filter and spatial-prefilter
columns.

## Importer (`unav_core.db.importer`)

```python
from unav_core.db import import_jsonl_to_db
summary = import_jsonl_to_db("samples/sample_catalog.jsonl", "data/unav.db", "sample")
print(summary.render())
```

- **Resilient read** — malformed/invalid lines are recorded, not fatal; valid
  objects still import.
- **Duplicate `uid` handling** — de-duplicated within the file *and* against
  existing rows; counts are reported separately.
- **`enrich=True`** — compute Cartesian `x/y/z` (Astropy) before storing, so
  sky-only inputs become 3D-queryable.
- **`ImportSummary`** fields: `dataset_id`, `dataset_name`, `source`,
  `objects_read`, `parse_errors`, `duplicates_in_file`, `duplicates_existing`,
  `inserted`, `error_details`.

`import_objects(db, objects, *, dataset_name=...)` is the in-process worker for
inserting already-built `CatalogObject` lists.

## Queries (`unav_core.db.queries`)

All return `list[CatalogObject]`:

| Function | Result |
| --- | --- |
| `search_by_name(db, query)` | name contains `query` (case-insensitive) |
| `filter_by_source(db, source)` | objects from a source |
| `filter_by_type(db, object_type)` | objects of a type (`ObjectType` or str) |
| `nearest_objects(db, x, y, z, limit=10)` | nearest in 3D (parsecs) |
| `objects_within_distance(db, x, y, z, max_distance_pc)` | within a 3D radius |
| `brightest_objects(db, limit=10)` | smallest apparent magnitude first |
| `highest_redshift_objects(db, limit=10)` | largest redshift first |

Cone (sky) search lives in `unav_core.db.spatial.cone_search` — see
[`SPATIAL_QUERY_STRATEGY.md`](SPATIAL_QUERY_STRATEGY.md).

## `Database`

```python
from unav_core.db import Database
db = Database("data/unav.db")     # or Database(":memory:")
db.count_objects()
db.dispose()
```

## CLI

```bash
python tools/import_catalog.py --input samples/sample_catalog.jsonl \
    --db data/unav.db --dataset-name sample
```

Add `--enrich` to compute Cartesian positions during import. (`data/` and
`*.db` are git-ignored.)
