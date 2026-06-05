# UNAV-SA — MVP Vertical Slice

The first **end-to-end** path that makes UNAV-SA actually run as a standalone
astronomical navigator with sample data — no external network, no Cinema 4D.

## The chain

```
 sample catalog ─▶ import into SQLite ─▶ local API server ─▶ standalone UI
   (JSONL)            (data/unav.db)        (FastAPI)          (static web)
                                                                  │
                            search ─ inspect ─ visible sector ─ 2D sky (RA/Dec)
```

| Step | Component | Entry point |
| --- | --- | --- |
| Generate sample catalog | `unav_core.data.sample_generator` | `tools/generate_sample_catalog.py` |
| Import into SQLite | `unav_core.db` (importer) | `tools/import_catalog.py` |
| Local API server | `unav_server` (FastAPI) | `tools/run_unav_server.py` |
| Standalone UI | `unav_app/static` (HTML/JS) | served at `/` by the server |
| Search / inspect | `GET /objects/search`, `GET /objects/{uid}` | UI search box + inspector |
| Visible sector | `POST /visible-sector/query` | UI button |
| 2D sky | `POST /sky/query-region` | UI canvas (RA/Dec) |

Everything in the chain already exists from earlier phases; this slice ties it
together and adds a **one-command demo**.

## One command

```bash
pip install -e ".[server]"
python scripts/run_demo.py
# → open the printed URL, e.g. http://127.0.0.1:8765/
```

`scripts/run_demo.py`:

1. generates `samples/sample_catalog.jsonl` if missing (100 objects, seed 42);
2. imports it into `data/unav.db` if the DB is missing/empty (with `--enrich`, so
   objects get Cartesian `x/y/z` for the visible sector);
3. starts the local API server (which also serves the UI);
4. prints the URL to open.

It is idempotent: re-running reuses the existing catalog and database. Use
`--fresh` to rebuild, `--open` to launch a browser, `--no-serve` to only prepare
data. See [`RUN_LOCAL_DEMO.md`](RUN_LOCAL_DEMO.md).

## What you can do in the UI

- See the **health** badge (`ok · N objects`) and the **dataset** list.
- **Search** by name/source/type; click a result.
- **Inspect** the selected object (uid, type, source, coordinates, …).
- **Query the visible sector** for the current navigator state.
- See objects in the **2D sky** (RA/Dec) view — pan/zoom, click to select.

## Acceptance criteria (and how they're met)

| Criterion | Met by |
| --- | --- |
| One command → see the local UI | `scripts/run_demo.py` (verified by a real server run + curl) |
| Sample objects appear in 2D | sky-region payload returns all 100 (each with RA/Dec); the canvas plots them |
| Search works | `/objects/search` against the local SQLite DB |
| Object inspection works | `/objects/{uid}` → the inspector panel |
| No external network | sample generation + import + API are all local |
| No Cinema 4D dependency | pure standalone engine + web UI |

## Tests

The slice is covered by `tests/test_mvp_vertical_slice.py` (the whole chain in one
test), plus the per-component tests: sample generation
(`test_sample_generator.py`), DB import (`test_db_importer.py`), API health/search
(`test_api_health.py`, `test_api_search.py`), and the visible-sector / sky
endpoints (`test_api_navigation.py`, `test_api_sky.py`). All run offline.
