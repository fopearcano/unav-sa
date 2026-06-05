# UNAV-SA

**UNAV-SA — a standalone, real-time astronomical data navigator.**

UNAV-SA is a standalone engine and application for exploring real astronomical
data in 2D/3D: querying catalogs, inspecting objects, planning routes/missions,
and navigating the sky and nearby space using authoritative data sources such as
**Gaia, SDSS, DESI and NASA/JPL**.

## What UNAV-SA is — and is not

- ✅ A **standalone astro-data navigation engine and application**.
- ❌ **Not** a Cinema 4D plugin.
- ❌ **Not** a render engine.
- ❌ **Not** bound to any DCC.

DCC integrations (Cinema 4D, Blender, Houdini, Unreal) are **future adapters** —
thin clients layered on top of the engine. See
[`docs/PRODUCT_IDENTITY.md`](docs/PRODUCT_IDENTITY.md).

## Quick start (one command)

Requires Python **3.10+**.

```bash
# 1. set up a virtual environment and install the demo dependencies
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,server]"

# 2. run the demo: generates sample data, imports it, starts the server + UI
python scripts/run_demo.py
# → open the printed URL, e.g. http://127.0.0.1:8765/
```

That's it — no external network, no Cinema 4D. The page gives you search, an
object inspector, a 2D sky map, a 3D point view, the navigator-state loop and
voyage planning (bookmarks / routes / missions).

> New here? `python scripts/setup_dev.py` prepares everything and prints a health
> check; `python scripts/healthcheck.py` tells you what's installed and missing.

## Developer scripts

| Command | Does |
| --- | --- |
| `python scripts/setup_dev.py` | create data dirs, generate sample data, print a health check + next steps (`--install` also pip-installs the extras) |
| `python scripts/run_demo.py` | generate + import sample data, then start the server + UI |
| `python scripts/run_server.py` | start the server + UI on the configured database |
| `python scripts/run_tests.py` | run the test suite (`--lint` also runs ruff); args forward to pytest |
| `python scripts/healthcheck.py` | report Python/dependency versions, config paths, sample/DB status (`--server` probes the server) |

See [`docs/DEVELOPER_WORKFLOW.md`](docs/DEVELOPER_WORKFLOW.md).

## Install dependencies

```bash
pip install -e ".[dev]"      # core engine + dev tooling (ruff, pytest, mypy)
pip install -e ".[server]"   # local API server (FastAPI + uvicorn)
pip install -e ".[query]"    # real catalog access (astroquery, pyvo) — optional
```

The core engine (astropy/numpy/pydantic/sqlalchemy) is always installed; the
**query** stack is optional and only needed to fetch real data. A missing optional
package is reported clearly by the health check and never breaks import/view.

## Generate sample data

```bash
python tools/generate_sample_catalog.py --count 100 --seed 42 \
    --output samples/sample_catalog.jsonl
```

Deterministic, offline synthetic objects (the demo does this for you).

## Run the server and open the UI

```bash
python scripts/run_server.py --port 8765   # serves the API + the UI at /
# open http://127.0.0.1:8765/
```

The server hosts the JSON API (`/docs` for interactive API docs) and the
standalone web UI at `/`.

## Fetch a Gaia sample and import it

Needs the **query** extra and network access:

```bash
python tools/fetch_gaia_region.py \
  --ra 56.75 --dec 24.12 --radius-deg 0.2 --limit 500 \
  --output data/catalogs/gaia_test.jsonl \
  --db data/unav.db --dataset-name gaia_test       # --db imports in one step
```

See [`docs/GAIA_WORKFLOW.md`](docs/GAIA_WORKFLOW.md) and, for the Solar System,
[`docs/JPL_SOLAR_SYSTEM_WORKFLOW.md`](docs/JPL_SOLAR_SYSTEM_WORKFLOW.md).

## Import data manually

```bash
python tools/import_catalog.py --input data/catalogs/gaia_test.jsonl \
    --db data/unav.db --dataset-name gaia_test --enrich   # --enrich fills x/y/z
```

## Configuration

Local paths, query caps and the server port are configurable via `UNAV_*`
environment variables (or a `.env` file — copy `.env.example`). Defaults are
project-relative (`data/` under the repo, `127.0.0.1:8765`). See
[`docs/LOCAL_CONFIGURATION.md`](docs/LOCAL_CONFIGURATION.md).

## Common problems

| Symptom | Fix |
| --- | --- |
| `The demo server needs FastAPI and uvicorn` | `pip install -e ".[server]"` |
| `astroquery is required …` when fetching | `pip install -e ".[query]"` (only needed for real data) |
| Empty UI / no objects | run `python scripts/run_demo.py` (or `--fresh` to rebuild); the health badge should read `ok · N objects` |
| Port already in use | `--port <other>` (or set `UNAV_SERVER_PORT`) |
| 3D panel says "unavailable" | your browser/environment lacks WebGL; the 2D view and the rest still work |
| Not sure what's installed/where data is | `python scripts/healthcheck.py` |

## Architecture at a glance

```
adapters/        Cinema 4D · Blender · Houdini · Unreal   (future, thin clients)
   │  (interchange / local API)
unav_server/     local API (FastAPI) + serves the UI
   │
unav_app/        standalone 2D/3D UI: search · inspect · navigate · routes/missions
   │
unav_core/       DCC-independent engine: astronomy + data + navigation logic
```

`unav_core` owns *all* astronomy/data logic (astropy + optional astroquery live
here, never in a DCC runtime). Full design:
[`docs/UNAV_SA_ARCHITECTURE.md`](docs/UNAV_SA_ARCHITECTURE.md).

## Documentation

| Document | Purpose |
| --- | --- |
| [DEVELOPER_WORKFLOW.md](docs/DEVELOPER_WORKFLOW.md) | Set up, run, test and develop locally |
| [LOCAL_CONFIGURATION.md](docs/LOCAL_CONFIGURATION.md) | `UNAV_*` settings and `.env` |
| [RUN_LOCAL_DEMO.md](docs/RUN_LOCAL_DEMO.md) | The one-command demo in detail |
| [GAIA_WORKFLOW.md](docs/GAIA_WORKFLOW.md) · [JPL_SOLAR_SYSTEM_WORKFLOW.md](docs/JPL_SOLAR_SYSTEM_WORKFLOW.md) | Real-data workflows |
| [VOYAGE_PLANNING_MVP.md](docs/VOYAGE_PLANNING_MVP.md) | Bookmarks, routes and missions |
| [UNAV_SA_ARCHITECTURE.md](docs/UNAV_SA_ARCHITECTURE.md) · [PRODUCT_IDENTITY.md](docs/PRODUCT_IDENTITY.md) | Design and identity |
| [ROADMAP.md](docs/ROADMAP.md) | Phased plan |

## License

License: **TBD**. To be decided before the first feature release.
