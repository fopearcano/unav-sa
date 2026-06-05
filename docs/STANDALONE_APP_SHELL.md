# UNAV-SA — Standalone App Shell

The first usable standalone UI: a minimal static web shell (`unav_app/static`)
served by the local API. It is intentionally small — it renders API responses and
posts user input, and contains **no backend logic**. Stack decision:
[`STANDALONE_APP_STACK.md`](STANDALONE_APP_STACK.md).

> Phase 10 scope. 2D is a canvas placeholder; 3D is a placeholder container
> (Three.js planned).

## Run it

```bash
pip install -e ".[server]"
# (optional) import the bundled sample catalog into a file DB first:
python tools/generate_sample_catalog.py --count 100 --seed 42 --output samples/sample_catalog.jsonl
python tools/import_catalog.py --input samples/sample_catalog.jsonl --db data/unav.db --dataset-name sample --enrich
# start the server (serves API + UI):
python tools/run_unav_server.py --db data/unav.db --port 8765
# open http://127.0.0.1:8765/
```

Without a `--db`, the server uses an in-memory database; use the UI's search after
importing via the API, or pass a file DB you've populated.

## What the shell shows

| Panel | Backed by |
| --- | --- |
| Health status (top bar) | `GET /health` |
| Datasets | `GET /datasets` |
| Search (name/source/type) + results | `GET /objects/search` |
| Selected object | `GET /objects/{uid}` |
| Navigator state (editable) | `GET`/`POST /navigator/state` |
| Focus on object | `POST /navigator/focus/{uid}` |
| Query visible sector | `POST /visible-sector/query` |
| 2D sky (RA/Dec) canvas | client-side render of the objects above |
| 3D view | placeholder container |

The 2D plot is a sky scatter (RA/Dec); objects with only Cartesian `x/y/z` (no
sky position) are listed but not plotted (the count is shown). The 3D viewport is
a labelled placeholder — Cartesian `x/y/z` rendering via Three.js comes later.

## How it connects

- Served by the FastAPI app at `/` (`create_app(..., serve_ui=True)` mounts
  `unav_app/static`). The API routes are registered first and take precedence;
  the static mount serves the UI and its assets.
- The page calls the API **same-origin** (relative URLs) — no CORS. Override the
  origin with `window.UNAV_API_BASE` if serving the UI elsewhere.

## Boundaries

- **No backend logic in the frontend.** Coordinates, queries, validation and
  navigation stay in `unav_core` / `unav_server`. The UI only fetches and renders.
- **No build step, no UI dependencies.** It is three static files.

See [`STANDALONE_APP_MANUAL_TEST.md`](STANDALONE_APP_MANUAL_TEST.md) for the
acceptance checklist.
