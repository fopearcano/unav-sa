# UNAV-SA — Run the Local Demo

Get the standalone navigator running with sample data in **one command**. No
external network, no Cinema 4D.

## Quick start

```bash
# 1. install the project with the local-server extras
pip install -e ".[server]"

# 2. run the demo
python scripts/run_demo.py

# 3. open the printed URL in a browser
#    http://127.0.0.1:8765/
```

That's it. The command generates the sample catalog (if missing), imports it into
a local SQLite database (if missing), and starts the local API server — which also
serves the standalone web UI. Stop it with Ctrl-C.

## What it does

```
✓ sample catalog: samples/sample_catalog.jsonl
✓ imported 100 objects → data/unav.db (enriched x/y/z)

UNAV-SA demo ready → open http://127.0.0.1:8765/
```

1. **Sample catalog** — `samples/sample_catalog.jsonl` (100 deterministic objects,
   seed 42). Generated if missing.
2. **Database** — `data/unav.db`. Imported (with `--enrich`, so objects get
   Cartesian `x/y/z`) if the DB is missing or empty. `data/` and `*.db` are
   git-ignored.
3. **Server + UI** — the local API at the printed URL, with the standalone UI at
   `/` and interactive API docs at `/docs`.

Re-running is **idempotent**: it reuses the existing catalog and database.

## In the UI

- Health badge and dataset list (top + left).
- **Search** (name / source / type) → results → click to **inspect** an object.
- **2D sky navigator** (RA/Dec): pan (drag), zoom (wheel), click a point to select.
- **Navigator state** panel + **Query visible sector**.
- A **3D** point view (if your browser supports WebGL).

## Options

```bash
python scripts/run_demo.py --help
```

| Flag | Default | Meaning |
| --- | --- | --- |
| `--db PATH` | `data/unav.db` | SQLite database path. |
| `--host` | `127.0.0.1` | Bind address (localhost). |
| `--port` | `8765` | Port. |
| `--count` | `100` | Sample objects to generate if missing. |
| `--seed` | `42` | Sample RNG seed. |
| `--fresh` | off | Rebuild the database from scratch. |
| `--open` | off | Open the UI in a browser automatically. |
| `--no-serve` | off | Prepare data and exit (don't start the server). |

## Troubleshooting

- **`The demo server needs FastAPI and uvicorn`** — install the extras:
  `pip install -e ".[server]"`.
- **Port already in use** — pass a different `--port`.
- **Empty UI / no objects** — ensure the import ran (`--fresh` rebuilds); the
  health badge should read `ok · 100 objects`.
- **3D panel says "unavailable"** — your browser/environment lacks WebGL; the 2D
  sky view and the rest of the app still work.

## Equivalent manual steps

The demo is a convenience wrapper around the existing tools:

```bash
python tools/generate_sample_catalog.py --count 100 --seed 42 \
    --output samples/sample_catalog.jsonl
python tools/import_catalog.py --input samples/sample_catalog.jsonl \
    --db data/unav.db --dataset-name sample --enrich
python tools/run_unav_server.py --db data/unav.db --port 8765
```

See [`MVP_VERTICAL_SLICE.md`](MVP_VERTICAL_SLICE.md) for the full chain and
[`STANDALONE_APP_SHELL.md`](STANDALONE_APP_SHELL.md) for the UI.
