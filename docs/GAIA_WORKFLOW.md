# UNAV-SA — Gaia Regional Import Workflow

The first real **external data** workflow: fetch a small Gaia DR3 region,
normalise it to UNAV records, import it into the local database, and view it in
the standalone navigator — with provenance preserved end to end.

```
 fetch_gaia_region.py ─▶ normalise ─▶ JSONL ─▶ import (--enrich) ─▶ SQLite ─▶ navigator
   (astroquery cone)     CatalogObject          x/y/z              DB         2D · 3D · inspect
```

> Requires the optional `astroquery` dependency and network access for the fetch
> step; everything after the JSONL is offline. Regional and **limited** by design
> (see [`DATA_FETCHING_SAFETY.md`](DATA_FETCHING_SAFETY.md)).

## 1. Install the query extra

```bash
pip install -e ".[query,server]"
```

If `astroquery` is missing, the fetch fails with a clear, actionable message
(`AstroqueryNotInstalledError`) — it is never required to import or view data.

## 2. Fetch a region to JSONL

```bash
python tools/fetch_gaia_region.py \
  --ra 56.75 --dec 24.12 \
  --radius-deg 0.2 \
  --limit 500 \
  --output data/catalogs/gaia_test.jsonl
```

A row-capped ADQL cone search against `gaiadr3.gaia_source`, normalised to
`CatalogObject` stars. `data/` is git-ignored — fetched catalogs are local
runtime data, never committed.

## 3. Fetch *and* import in one step

Add `--db` (and an optional `--dataset-name`) to import straight into the local
database, enriching Cartesian `x/y/z` for the 3D view:

```bash
python tools/fetch_gaia_region.py \
  --ra 56.75 --dec 24.12 \
  --radius-deg 0.2 \
  --limit 500 \
  --output data/catalogs/gaia_test.jsonl \
  --db data/unav.db \
  --dataset-name gaia_test
```

(Equivalent to a separate `tools/import_catalog.py --input … --db … --enrich`.)

## 4. View in the navigator

```bash
python tools/run_unav_server.py --db data/unav.db --port 8765
# open http://127.0.0.1:8765/
```

- The **dataset list** (left panel) shows `gaia_test · Gaia DR3`.
- **Search** by name (`Gaia DR3 …`), source (`Gaia DR3`) or type (`star`).
- Click a result to **inspect**: the panel shows the Gaia fields (ra/dec,
  parallax, distance, magnitude, colour index, proper motion, radial velocity)
  **and the provenance** (source, catalog, epoch `J2016.0`, endpoint, retrieved
  time).
- **2D sky** plots each star by RA/Dec; **3D** shows the enriched `x/y/z`.

## Normalised fields

| Output field | From |
| --- | --- |
| `uid` | `gaia:{source_id}` |
| `source` | `Gaia DR3` (fixed) |
| `object_type` | `star` (fixed) |
| `ra_deg`, `dec_deg` | `ra`, `dec` (ICRS) |
| `parallax_mas` | `parallax` (kept raw; may be ≤ 0) |
| `distance_pc` | `1000 / parallax` — **only when parallax > 0** |
| `apparent_magnitude` | `phot_g_mean_mag` |
| `color_index` | `bp_rp` |
| `proper_motion_ra_masyr`, `proper_motion_dec_masyr` | `pmra`, `pmdec` |
| `radial_velocity_kms` | `radial_velocity` |
| `metadata` | `{gaia_source_id}` |
| `provenance` | `Gaia DR3`, table `gaiadr3.gaia_source`, epoch `J2016.0`, query params |
| `x`, `y`, `z` | computed on import with `--enrich` (from ra/dec/distance) |

Missing/masked/NaN cells become `None`. The per-object provenance is persisted in
the database and returned by `GET /objects/{uid}`, so it appears in the inspector.

## Safety

- **Default limit 500**; a `--limit` above **5000** prints a warning and is
  discouraged (UNAV-SA is for regional, limited fetches — not survey mirrors).
- **Radius cap**: a radius above **5°** is refused unless `--allow-large-radius`.
- **No astroquery → clear error**, with install instructions; import/view never
  need it.
- Fetched catalogs and the working DB live under git-ignored `data/`.

## Testing (no network)

All Gaia tests use **mocked** astroquery responses — no network, deterministic:

- `tests/test_gaia_connector.py` — normalisation, the distance-from-parallax
  rule, masking, ADQL region/limit, radius cap, the 5000 warning, and the
  missing-astroquery / network / empty / malformed error paths.
- `tests/test_gaia_workflow.py` — the full fetch → write → import → search →
  inspect chain (provenance visible) and the `fetch_gaia_region.py` CLI with
  `--db` direct import.
- `tests/test_db_importer.py` — per-object field + provenance round-trip.
