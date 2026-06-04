# UNAV-SA — Roadmap

A phased plan from the current foundation to a navigable standalone application
and, later, DCC adapters. Phases are ordered by dependency, not by date.

## Phase 0 — Foundation *(this milestone)*

- [x] Project structure: `unav_core`, `unav_app`, `unav_server`, `adapters`.
- [x] Architecture & strategy documents.
- [x] Python project scaffolding: `pyproject.toml`, requirements, `.gitignore`.
- [x] Import smoke tests for the three top-level packages.
- [ ] Choose a license (currently **TBD**).

**Explicit non-goals for this phase:** no data fetching, no UI, no Cinema 4D
adapter.

## Phase 1 — Core primitives

- `unav_core.astro`: coordinates, time and units on top of astropy.
- `unav_core.data`: canonical catalog schema + record validation (pydantic).
- `unav_core.provenance`: provenance model attached to records.
- Unit tests for transforms, schema validation and provenance.

## Phase 2 — Local cache & spatial queries

- `unav_core.db`: SQLite/SQLAlchemy local cache with a spatial index.
- Cone / box / volume **regional** query API over cached data.
- Cache keying, expiry and provenance persistence.

## Phase 3 — Connectors (real data, regionally)

- `unav_core.connectors`: first connector (e.g. **Gaia** via TAP/astroquery),
  then SIMBAD/VizieR; later SDSS, DESI, NASA/JPL Horizons, MAST.
- Regional queries only; results normalised → validated → provenance → cached.
- Strict result caps and responsible-access defaults.

## Phase 4 — Navigation & routes/missions

- `unav_core.navigation`: observer/target state and the real-time update loop.
- `unav_core.routes` and `unav_core.missions`: build, save and replay.
- `unav_core.export`: interchange serialisation for app and adapters.

## Phase 5 — Standalone application

- `unav_app`: 2D map / 3D space viewport, catalog search, object inspection,
  navigator control, route/mission editing.
- A first end-to-end loop: query a region → inspect → navigate.

## Phase 6 — Local server

- `unav_server`: local HTTP API exposing the core (FastAPI/uvicorn).
- Future WebSocket **state sync** for real-time navigation.

## Phase 7 — DCC adapters

- **Cinema 4D first** — a thin client over interchange/API. Then Blender,
  Houdini, Unreal.
- No heavy scientific dependencies inside any host runtime.

## Cross-cutting (ongoing)

- Provenance and validation everywhere; reproducible views and missions.
- Conservative dependencies; heavy science confined to core/app/server.
- Tests and documentation kept in step with each phase.
