# UNAV-SA — SQLite Schema

The concrete SQLite schema of the local cache, as defined in
`unav_core.db.schema` (SQLAlchemy Core). **SQLite is the baseline** backend —
local-first and simple; no DuckDB, no Postgres. See
[`LOCAL_DATABASE.md`](LOCAL_DATABASE.md) for the design rationale and
[`SPATIAL_QUERY_STRATEGY.md`](SPATIAL_QUERY_STRATEGY.md) for queries.

> The database stores **normalized `CatalogObject`s** (a bounded local working
> set), not a full survey mirror. `data/` is git-ignored runtime state.

## Tables

### `objects` — one row per catalog object

The scalar fields of `CatalogObject` plus a per-object provenance JSON:

```
uid                      TEXT  PRIMARY KEY     -- globally unique UNAV id
source                   TEXT  NOT NULL
object_type              TEXT  NOT NULL
name                     TEXT
native_id                TEXT                  -- source-native id
ra_deg                   REAL
dec_deg                  REAL
distance_pc              REAL
parallax_mas             REAL
redshift                 REAL
radial_velocity_kms      REAL
proper_motion_ra_masyr   REAL
proper_motion_dec_masyr  REAL
apparent_magnitude       REAL
absolute_magnitude       REAL
color_index              REAL
spectral_type            TEXT
x                        REAL                  -- ICRS Cartesian, parsecs
y                        REAL
z                        REAL
provenance_json          TEXT                  -- the object's Provenance, JSON
```

`x/y/z` are **parsec Cartesian** coordinates (see
[`COORDINATE_CONVENTIONS.md`](COORDINATE_CONVENTIONS.md)); they are populated by
enrichment on import and are what spatial queries use.

### `metadata` — lazy, separate per-object extras

```
uid            TEXT  PRIMARY KEY   -- 1:1 with objects
metadata_json  TEXT  NOT NULL
```

Stored **only** for objects with non-empty metadata and joined back on read, so
the common path never pays for free-form extras.

### `datasets` — one row per import/query

```
dataset_id             TEXT  PRIMARY KEY
name                   TEXT  NOT NULL
source                 TEXT  NOT NULL
object_count           INTEGER
created_at             TEXT             -- ISO-8601 UTC
query_parameters_json  TEXT
```

The richer dataset metadata (`description`, `coordinate_system`, `units`) lives on
the `Dataset` model and in the per-dataset provenance JSON below.

### `provenance` — per-dataset provenance

```
dataset_id       TEXT  PRIMARY KEY
provenance_json  TEXT  NOT NULL
```

Provenance is recorded at **dataset** granularity here, **and** per-object in
`objects.provenance_json`.

### Planning tables (`bookmarks`, `routes`, `missions`)

`<id>`, `created_at`, `data_json` — the voyage-planning models stored as JSON
(see [`ROUTES_BOOKMARKS_MISSIONS.md`](ROUTES_BOOKMARKS_MISSIONS.md)). Part of the
same database so plans persist with the catalog.

## Indexes

On the `objects` table, covering the filter and spatial-prefilter columns:

`source`, `object_type`, `(ra_deg, dec_deg)`, `x`, `y`, `z`, `distance_pc`,
`redshift`, `apparent_magnitude`.

These make source/type filtering, the 2D RA/Dec box, and the 3D bounding-box
prefilter fast on a bounded working set.

## Row ↔ object mapping

`unav_core.db.schema` provides `object_core_values(obj)` (object → row values) and
`row_to_object(row, metadata)` (row → `CatalogObject`). Every scalar field plus
provenance round-trips; metadata is supplied from the `metadata` table. These (and
the tables) are re-exported from `unav_core.db.models` for discoverability.

## Notes vs. a "from-scratch" schema

The implemented schema keeps the object's batch link in the **datasets/provenance**
tables rather than a denormalised `objects.dataset_id` column, and stores dataset
units/coordinate-system in the `Dataset` model + provenance JSON rather than
separate columns. The columns above are the source of truth.
