# UNAV-SA — Standalone App Stack (decision)

This records the decision for the **first** standalone app shell (Phase 10).
Keep it minimal; do not overbuild the UI.

## Decision

**A dependency-free static web frontend served by the local API server.**

- **Backend:** the existing `unav_server` FastAPI local API (Phase 9). All logic
  stays server-side in `unav_core`.
- **Frontend:** plain **HTML + CSS + vanilla JS** under `unav_app/static/`. No
  Node, no bundler, no framework, no CDN dependencies.
- **Serving:** the FastAPI server optionally mounts `unav_app/static` at `/`, so
  one process serves both the API and the UI. The UI calls the API **same-origin**
  (relative URLs) — no CORS needed.
- **2D now:** a `<canvas>` sky (RA/Dec) scatter placeholder.
- **3D later:** a placeholder container; **Three.js** will be added in a future
  phase to render the Cartesian (`x/y/z`, parsec) view.

## Why this (and not the alternatives)

| Option | Verdict |
| --- | --- |
| Vanilla static HTML/JS (chosen) | Zero toolchain, runs anywhere Python runs, fastest path to a usable shell. |
| Vite/React/Svelte app | Real build tooling + Node; overkill for a first shell. Revisit if the UI grows. |
| Native desktop (PySide/Tk) | Heavier, less portable than a browser; web is the documented direction. |
| Electron/Tauri | Packaging concern, not needed yet; a browser tab is enough now. |

The web approach also matches the product direction: the same API/interchange a
DCC **adapter** uses (see [`ADAPTER_COMMUNICATION_MODEL.md`](ADAPTER_COMMUNICATION_MODEL.md)).

## Boundaries (do not cross)

- **No backend logic in the frontend.** The UI only renders API responses and
  posts user input. Coordinates, queries, validation and navigation stay in
  `unav_core` / `unav_server`.
- **No new runtime dependencies** for the UI. It is static files.

## Future

- Add **Three.js** (vendored locally, still no build step) for the 3D viewport.
- If the UI grows enough to need components/state management, introduce **Vite**
  under `unav_app/web/` then — and document the migration. Until then, static
  files under `unav_app/static/`.

See [`STANDALONE_APP_SHELL.md`](STANDALONE_APP_SHELL.md) for what the shell does
and [`STANDALONE_APP_MANUAL_TEST.md`](STANDALONE_APP_MANUAL_TEST.md) for the
acceptance checklist.
