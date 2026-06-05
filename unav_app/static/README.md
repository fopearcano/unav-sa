# UNAV-SA — Standalone Web Shell (static)

A minimal, dependency-free web UI for UNAV-SA: plain `index.html` + `style.css`
+ `app.js`. **No Node, no bundler, no CDN.** See
[`docs/STANDALONE_APP_STACK.md`](../../docs/STANDALONE_APP_STACK.md).

## Run

The local API server serves this UI at `/`:

```bash
pip install -e ".[server]"
python tools/run_unav_server.py --db data/unav.db --port 8765
# open http://127.0.0.1:8765/
```

The page calls the API **same-origin** (relative URLs), so no CORS setup is
needed. To point the UI at a different API origin, set
`window.UNAV_API_BASE = "http://host:port"` before `app.js` loads.

## What it does

Health status, datasets, catalog search, object inspection, navigator-state
editing, a visible-sector query, a 2D sky (RA/Dec) canvas scatter, and a 3D
placeholder container (Three.js planned). It contains **no backend logic** — it
only renders API responses. See
[`docs/STANDALONE_APP_SHELL.md`](../../docs/STANDALONE_APP_SHELL.md).
