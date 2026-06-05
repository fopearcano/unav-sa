# UNAV-SA — JPL Horizons Solar System Workflow

Fetch **static epoch positions** for Solar System bodies from NASA/JPL Horizons,
normalise them (with 3D `x/y/z`), import them into the local database, and view
them in the standalone navigator.

```
 fetch_jpl_*.py ─▶ normalise + classify ─▶ JSONL ─▶ import (--enrich) ─▶ SQLite ─▶ navigator
   (Horizons)       CatalogObject + x/y/z          (idempotent)        DB         3D · inspect
```

> Requires the optional `astroquery` dependency and network access for the fetch
> step; everything after the JSONL is offline. These are **snapshots at one
> epoch**, not trajectories — see [`EPOCH_OBJECTS.md`](EPOCH_OBJECTS.md).

## 1. Install the query extra

```bash
pip install -e ".[query,server]"
```

A missing `astroquery` fails the fetch with a clear, actionable message — it is
never required to import or view data.

## 2. Fetch one body

```bash
python tools/fetch_jpl_body.py \
  --body Mars \
  --epoch 2026-01-01T00:00:00 \
  --center 500@10 \
  --output data/catalogs/jpl_mars.jsonl
```

`--epoch` is an ISO-8601 time or a Julian Date. `--center` is a Horizons
observer/location code (default `@sun`, heliocentric). The body **type** is
classified from its name (`Mars` → planet) unless `--type` is given. Add
`--db`/`--dataset-name` to import in the same step.

## 3. Fetch the Solar System and import

```bash
python tools/fetch_jpl_solar_system.py \
  --epoch 2026-01-01T00:00:00 \
  --bodies Mercury,Venus,Earth,Mars,Jupiter,Saturn,Uranus,Neptune,Pluto,Moon \
  --output data/catalogs/jpl_solar_system.jsonl \
  --db data/unav.db \
  --dataset-name jpl_solar_system_2026
```

`--bodies` is comma-separated; well-known planet/moon names are classified
automatically (use `name=type` to override, e.g. `Ceres=asteroid`). `--db`
imports the result (enriching `x/y/z`). `data/` is git-ignored.

## 4. View in the navigator

```bash
python tools/run_unav_server.py --db data/unav.db --port 8765
# open http://127.0.0.1:8765/
```

- The **dataset list** shows `jpl_solar_system_2026 · JPL Horizons`.
- **Search** by type `planet` (or `moon`), or by name (`Mars`, `Jupiter`).
- The bodies render in **3D** with **distinct type colours** (planets green,
  moons grey, …). A JPL-only view auto-frames to the Solar System's scale.
- **Inspect** a body: the panel shows its position and the **epoch** and
  **center** (in the metadata section) plus the provenance (epoch, endpoint,
  retrieved time).

## Normalised fields

| Output field | From |
| --- | --- |
| `uid` | `jpl:{body}:{epoch}` (unique per body **and** epoch) |
| `source` | `JPL Horizons` (fixed) |
| `object_type` | `planet`/`moon`/`asteroid`/`comet`/`unknown` (classified by name or `--type`) |
| `name` | Horizons `targetname` (else the body id) |
| `ra_deg`, `dec_deg` | apparent `RA`, `DEC` (ICRS, center-relative) |
| `distance_pc` | `delta` (AU) → parsecs |
| `x`, `y`, `z` | ICRS Cartesian (parsecs), enriched from ra/dec/distance |
| `apparent_magnitude` | `V` (when present) |
| `metadata` | `{body, center, epoch, distance_au, targetname}` |
| `provenance` | `JPL Horizons`, frame `ICRS`, epoch, endpoint, query params |

> Solar System distances are AU-scale, so `x/y/z` are **tiny in parsecs** — the
> bodies cluster near the origin in a galactic (parsec) view. View a JPL-only
> dataset (it auto-frames) for a Solar System layout. See
> [`EPOCH_OBJECTS.md`](EPOCH_OBJECTS.md).

## Safety

- Per-body queries; no bulk download. A missing `astroquery` fails clearly.
- Fetched catalogs and the working DB live under git-ignored `data/`.

## Testing (no network)

All JPL tests use **mocked** Horizons responses:

- `tests/test_jpl_connector.py` — normalisation, name classification, enriched
  `x/y/z`, epoch (JD/ISO), and the error paths (missing astroquery / network /
  empty / malformed).
- `tests/test_jpl_workflow.py` — the full fetch → import → search (planets) → 3D
  → inspect (epoch/center) chain, and the `fetch_jpl_solar_system.py` CLI with
  `--db`.
