# UNAV-SA — Local Configuration

Local paths, query caps and the server defaults are configurable, so a developer
can point UNAV-SA at a different data directory, database, port or limits without
editing code. Configuration is resolved by `unav_core.config` from environment
variables over project-relative defaults.

## Settings

| Setting | Env var | Default |
| --- | --- | --- |
| Data directory | `UNAV_DATA_DIR` | `<repo>/data` |
| Database path | `UNAV_DB_PATH` | `<DATA_DIR>/unav.db` |
| Cache directory | `UNAV_CACHE_DIR` | `<DATA_DIR>/cache` |
| Samples directory | `UNAV_SAMPLES_DIR` | `<repo>/samples` |
| Default query limit | `UNAV_QUERY_LIMIT` | `500` |
| Default max cone radius (deg) | `UNAV_MAX_RADIUS_DEG` | `5.0` |
| Server host | `UNAV_SERVER_HOST` | `127.0.0.1` |
| Server port | `UNAV_SERVER_PORT` | `8765` |

`UNAV_DB_PATH` and `UNAV_CACHE_DIR` default **under** `UNAV_DATA_DIR`, so setting
just `UNAV_DATA_DIR` moves the whole working set; set `UNAV_DB_PATH` to place the
database elsewhere explicitly.

## How to set them

Three equivalent ways (highest precedence first):

1. **Environment variables** — `UNAV_SERVER_PORT=9000 python scripts/run_demo.py`.
2. **A `.env` file** — copy `.env.example` to `.env` and uncomment lines. Scripts
   load it on start (without overriding variables already set in the environment).
3. **Defaults** — project-relative, as in the table above.

Example `.env`:

```
UNAV_DATA_DIR=/data/unav
UNAV_SERVER_PORT=9000
UNAV_QUERY_LIMIT=1000
```

## Using it in code

```python
from unav_core.config import load_config
cfg = load_config()                 # reads os.environ over defaults
cfg.database_path                   # Path to the SQLite DB
cfg.server_host, cfg.server_port    # server bind defaults
cfg.default_query_limit             # regional-fetch row cap
cfg.sample_catalog_path             # <samples>/sample_catalog.jsonl
cfg.ensure_dirs()                   # mkdir data/ and cache/
```

`load_config(env=..., root=...)` accepts an explicit env mapping and project root
(used in tests); `apply_dotenv(root)` loads a `.env` into `os.environ` without
overriding existing variables.

`Config` is a frozen dataclass and importing `unav_core.config` pulls in **no**
heavy dependencies (stdlib only), so configuration can be read early and anywhere.

## Where the scripts use it

`run_demo.py`, `run_server.py`, `setup_dev.py` and `healthcheck.py` resolve their
database path, host and port from `load_config()` (overridable with their own
flags). `healthcheck.py` prints the resolved configuration so you can confirm
where data will be read from and written to. See
[`DEVELOPER_WORKFLOW.md`](DEVELOPER_WORKFLOW.md).

## Notes

- The query caps mirror the connector safety limits
  ([`DATA_FETCHING_SAFETY.md`](DATA_FETCHING_SAFETY.md)): UNAV-SA fetches
  regional, limited data — not full survey mirrors.
- `data/` (the working DB, cache and any fetched catalogs) is **git-ignored**
  runtime state; only curated `samples/` are committed.
