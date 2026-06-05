# UNAV-SA — Developer Workflow

Everything a new contributor needs to **run, test and develop** UNAV-SA locally.
No external network and no Cinema 4D required for the core loop.

## Prerequisites

- Python **3.10+**.
- A virtual environment is recommended.

## One-time setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,server]"      # core engine + dev tooling + local server
python scripts/setup_dev.py         # create data dirs, sample data, health check
```

`scripts/setup_dev.py` is idempotent: it creates the data/cache directories,
generates the sample catalog if missing, prints a health check and the next
steps. Add `--install` to have it run the `pip install -e ".[dev,server]"` for
you, or `--extras dev,server,query` to include real-data access.

## The one-command scripts

| Script | Purpose |
| --- | --- |
| `scripts/setup_dev.py` | prepare dirs + sample data, print health + next steps (`--install`) |
| `scripts/run_demo.py` | generate + import sample data, then serve the API + UI |
| `scripts/run_server.py` | serve the API + UI on the configured database |
| `scripts/run_tests.py` | run the test suite (`--lint` also runs ruff); extra args → pytest |
| `scripts/healthcheck.py` | report env/deps/config/data status (`--server` probes the server) |

Each is a small Typer CLI (`--help` on any of them). They resolve their defaults
(database path, host/port) from the local configuration
([`LOCAL_CONFIGURATION.md`](LOCAL_CONFIGURATION.md)).

## Run the app

```bash
python scripts/run_demo.py            # prepare data + serve, then open the URL
python scripts/run_demo.py --fresh    # rebuild the database first
python scripts/run_server.py          # just serve the configured DB
```

Open the printed URL (default `http://127.0.0.1:8765/`). The page serves the
whole app: search, inspector, 2D sky, 3D points, the navigator-state loop and
voyage planning. Interactive API docs are at `/docs`.

## Run the tests — one command

```bash
python scripts/run_tests.py            # == python -m pytest
python scripts/run_tests.py --lint     # ruff check + ruff format --check, then pytest
python scripts/run_tests.py -k voyage  # extra args forward to pytest
```

The whole suite runs **offline** (real-data connectors are tested with mocked
responses). Equivalently: `pytest`, `ruff check .`, `ruff format --check .`.

## Health check

```bash
python scripts/healthcheck.py          # deps, config paths, sample/DB status
python scripts/healthcheck.py --server # also probe the configured server URL
```

It lists Python + dependency versions, **explains which optional packages are
missing and how to install them** (e.g. `astroquery` → `pip install -e
".[query]"`), shows the resolved data/DB/cache paths and query caps, and reports
whether the sample catalog and database exist (with object counts). Exit code is
non-zero if a **core** dependency is missing. The same report is available
programmatically via `unav_core.health.health_report()`.

## Project layout

```
unav_core/   DCC-independent engine: astro · data · connectors · db · navigation ·
             routes · missions · provenance · config · health
unav_app/    standalone 2D/3D web UI (static; served by the server)
unav_server/ local FastAPI server (API + serves the UI)
tools/       per-task CLIs (sample gen, import, fetch Gaia/JPL, run server)
scripts/     one-command developer entry points (this doc)
tests/       offline test suite
samples/     committed example data; data/ is git-ignored runtime state
```

## Typical dev loop

1. Change code under `unav_core` / `unav_server` / `unav_app/static`.
2. `python scripts/run_tests.py --lint` (fast, offline).
3. `python scripts/run_demo.py` and exercise the UI.
4. `python scripts/healthcheck.py` if something looks off (missing dep / wrong path).

## Working with real data (optional)

```bash
pip install -e ".[query]"        # astroquery + pyvo
python tools/fetch_gaia_region.py --ra 56.75 --dec 24.12 --radius-deg 0.2 \
    --limit 500 --output data/catalogs/gaia_test.jsonl --db data/unav.db \
    --dataset-name gaia_test
```

See [`GAIA_WORKFLOW.md`](GAIA_WORKFLOW.md) and
[`JPL_SOLAR_SYSTEM_WORKFLOW.md`](JPL_SOLAR_SYSTEM_WORKFLOW.md). Fetched data and
the working database live under the git-ignored `data/` directory.

## Conventions

- **Lint/format:** ruff (line length 100; `E,F,I,UP,B`). Run via `--lint`.
- **Imports stay light:** `import unav_core` pulls in nothing heavy; astropy is
  lazy, astroquery is optional. Keep it that way.
- **No DCC dependency** anywhere in `unav_core`/`unav_app`/`unav_server`.
