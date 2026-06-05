# UNAV-SA — Offline Demo Data

How to get a working UNAV-SA dataset **with no network access and no real catalog
queries** — for development, tests, demos and offline workflows. It uses only the
deterministic synthetic [sample catalog](SAMPLE_DATA.md).

> The sample data is **synthetic** and **for testing/demo only** — it is *not*
> scientifically authoritative and is not from any real survey. Source labels are
> deliberately `sample-…`/synthetic so it is never mistaken for real data.

## One command

```bash
python scripts/create_sample_db.py --db data/unav_sample.db
```

This generates the sample catalog (if missing), initializes a local SQLite
database, imports the catalog (enriching Cartesian `x/y/z`), and prints a summary.
It is **idempotent** — re-running reuses the existing catalog and database
(use `--fresh` to rebuild).

```
✓ sample catalog: samples/sample_catalog.jsonl
✓ imported 100 objects → data/unav_sample.db (enriched x/y/z)

data/unav_sample.db — 100 objects, 1 dataset(s)
  sample-gaia: 50
  ...
  star: 50
  galaxy: 25
  ...
```

## Step by step

```bash
# 1. generate the deterministic sample catalog (100 objects, seed 42)
python tools/generate_sample_catalog.py --count 100 --seed 42 \
    --output samples/sample_catalog.jsonl

# 2. create + populate the SQLite database from it
python scripts/create_sample_db.py \
    --catalog samples/sample_catalog.jsonl --db data/unav_sample.db

# 3. inspect the database
python tools/db_info.py --db data/unav_sample.db
```

`db_info` prints the dataset count, object count, and **per-source / per-object-
type counts** (see [`SQLITE_SCHEMA.md`](SQLITE_SCHEMA.md)).

## What you get

- ~**100** deterministic synthetic objects: nearby/distant stars, galaxies,
  quasars, Solar-System placeholder bodies and custom navigation objects (see
  [`SAMPLE_DATA.md`](SAMPLE_DATA.md) for the exact mix and fields).
- The same `(count, seed)` always produces the **same** catalog (byte-for-byte),
  so tests and demos are reproducible.
- Stars/solar/custom objects carry enriched `x/y/z` (parsecs) for 3D queries;
  redshift-only galaxies/quasars stay sky-only.

## Why offline-first

UNAV-SA must be runnable and testable **without** the internet or real archive
access. The sample data lets the whole pipeline — generate → import → search →
spatial query → navigate — work entirely locally. Fetching real data
(Gaia/SDSS/DESI/JPL) is a separate, optional **connector** concern (Phase 5+).

## Where it lives

- The committed example catalog is `samples/sample_catalog.jsonl` (small, ~100
  objects) and **is** version-controlled.
- Generated databases and any working catalogs live under the **git-ignored**
  `data/` directory — they are local runtime state, never committed.

See also: [`SAMPLE_DATA.md`](SAMPLE_DATA.md),
[`DB_IMPORT_WORKFLOW.md`](DB_IMPORT_WORKFLOW.md),
[`RUN_LOCAL_DEMO.md`](RUN_LOCAL_DEMO.md).
