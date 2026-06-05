# UNAV-SA — Local API Server

`unav_server` exposes `unav_core` over a **local HTTP API** (FastAPI) so the
standalone app and future DCC adapters can talk to one running engine. It is a
thin transport/orchestration layer — **no astronomy logic lives here**.

> Phase 9 scope. FastAPI/uvicorn are *optional* dependencies (the `server`
> extra). `import unav_server` stays light; FastAPI is pulled in only via
> `create_app`.

## Running

```bash
pip install -e ".[server]"
python tools/run_unav_server.py --db data/unav.db --port 8765
```

The server binds to `127.0.0.1` by default — it is a **local** API. Interactive
docs are available at `http://127.0.0.1:8765/docs` (FastAPI/OpenAPI).

Programmatically:

```python
from unav_server import create_app
app = create_app("data/unav.db")   # a FastAPI app
```

## Architecture

```
HTTP client (app / adapter)
        │
   unav_server.api      (FastAPI router — thin)
        │
   unav_server.state_service.StateService   (orchestration + runtime state)
        │
   unav_core  (db · navigation · routes · missions · data)
```

- **`app.py`** — `create_app(db_path)` builds the FastAPI app, attaches a
  `StateService` to `app.state`, and mounts the router.
- **`api.py`** — the endpoints; each maps a request to a `StateService` call.
- **`state_service.py`** — holds the `Database` handle, the current
  `NavigatorState`, and the routes/missions store; composes `unav_core`.
- **`models.py`** — request/response DTOs (and reuse of core models).

## Runtime state & persistence

- The **navigator state** is held in memory (set via `POST /navigator/state`,
  read via `GET /navigator/state`, updated by `POST /navigator/focus/{uid}`).
- **Objects/datasets** are persisted in the local SQLite cache (`unav_core.db`).
- **Routes/missions** are stored **in memory** for this phase (they reset when
  the server restarts). Durable route/mission storage is future work; they are
  already fully JSON-serialisable (see [`MISSIONS.md`](MISSIONS.md)).

## Endpoints

See [`API_ENDPOINTS.md`](API_ENDPOINTS.md) for the full list. Acceptance checks
covered by the tests: the server starts, `/health` works, search runs against the
local DB, navigator state can be set/read, and `/visible-sector/query` returns
objects.

## Security note

`POST /datasets/import-jsonl` reads a **server-local** file path. The API is
intended for localhost use by the app/adapters on the same machine; do not expose
it to untrusted networks.
