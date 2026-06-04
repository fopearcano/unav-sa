# UNAV-SA — Architecture

UNAV-SA is a **standalone, real-time astronomical data navigator**. This
document describes its layered architecture and the responsibilities of each
component. It is the authoritative map from concepts to packages.

For the product boundary (what UNAV-SA is and is not) see
[`PRODUCT_IDENTITY.md`](PRODUCT_IDENTITY.md).

## Design principles

1. **The core is independent from any DCC.** `unav_core` knows nothing about
   Cinema 4D, Blender, Houdini or Unreal.
2. **Astronomy lives in the core.** Astropy is expected in the standalone/core
   environment; astroquery/pyvo may be used for catalog access where
   appropriate.
3. **Heavy dependencies stay out of DCC runtimes.** Scientific libraries are
   confined to the core, app and server — never a plugin runtime.
4. **Real data, regionally.** Support regional queries, a local cache,
   provenance, validation and real-time navigation. Never bulk-download whole
   catalogs by default.
5. **Adapters are clients.** DCC integrations consume data; they do not own
   astronomy logic.
6. **Cheap, side-effect-free imports.** Importing a package performs no network
   I/O; heavy dependencies are imported lazily inside submodules.

## Layered overview

```
┌─────────────────────────────────────────────────────────────────────┐
│ adapters/   Cinema 4D (first) · Blender · Houdini · Unreal  (future)  │
│             thin clients — consume interchange / call the local API   │
└───────────────▲─────────────────────────────────────────────────────┘
                │  interchange payloads / local API + (future) state sync
┌───────────────┴─────────────────────────────────────────────────────┐
│ unav_server/   local API · future WebSocket state sync · adapter comms│
└───────────────▲─────────────────────────────────────────────────────┘
                │  in-process or local API
┌───────────────┴─────────────────────────────────────────────────────┐
│ unav_app/    standalone 2D/3D UI                                      │
│              search · inspect · navigator control · routes/missions   │
│              desktop · viewport · ui                                   │
└───────────────▲─────────────────────────────────────────────────────┘
                │  direct Python API
┌───────────────┴─────────────────────────────────────────────────────┐
│ unav_core/   DCC-INDEPENDENT ENGINE — all astronomy & data logic      │
│                                                                       │
│  astro ─ data ─ connectors ─ db ─ navigation ─ routes ─ missions ─    │
│  export ─ provenance                                                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## UNAV Core (`unav_core/`)

The DCC-independent engine. It owns every astronomy and data concern. Mapping
from concept to package:

| Concept | Package | Responsibility |
| --- | --- | --- |
| **Coordinates** | `astro` | Sky frames (ICRS, Galactic, ecliptic), RA/Dec, proper motion, parallax/distance, frame transforms (astropy-backed). |
| **Time** | `astro` | Epochs and time scales (UTC/TT/TDB), epoch propagation. |
| **Units** | `astro` | One canonical unit registry shared by all layers. |
| **Catalog schema** | `data` | Canonical, source-independent models for astronomical objects and catalog records. |
| **Validation** | `data` (+ `provenance`) | Every record is normalised and validated (pydantic) on entry; provenance is validated alongside. |
| **Spatial queries** | `db` (+ `data`) | Cone/box/region lookups against cached data via a spatial index; request models defined in `data`. |
| **Provenance** | `provenance` | Source, query parameters, catalog/version, timestamps, unit/frame assumptions — attached to records and carried everywhere. |
| **Navigation state** | `navigation` | Observer/camera pose, reference frame, FOV, target selection and the real-time update loop. |
| **Routes** | `routes` | Ordered waypoints/targets describing a path to follow. |
| **Missions** | `missions` | Persistable scenarios composing routes, targets, timing and navigation parameters. |
| **Export / interchange** | `export` | Portable serialisation of objects, regions, routes, missions and navigation state for files and adapters. |
| **Data-source connectors** | `connectors` | Translate regional UNAV queries to Gaia/SDSS/DESI/NASA-JPL/SIMBAD/VizieR/MAST requests and map responses onto the canonical schema. *(Not implemented yet.)* |
| **Local cache** | `db` | Bounded local working set (SQLAlchemy over a SQLite baseline) — never a full survey mirror. |

### Data flow (illustrative, target design)

```
region request
   → connectors (regional query to a real source, e.g. Gaia)
   → data (normalise + validate into the canonical schema)
   → provenance (attach source/query/time/version)
   → db (cache the bounded working set; build spatial index)
   → navigation (drive the real-time observer/target state)
   → export (interchange for app viewport and DCC adapters)
```

> None of the fetching/UI logic above is implemented in this milestone — it is
> the architecture the packages are scaffolded for.

---

## UNAV App (`unav_app/`)

The standalone application that *uses* the core. It contains **no** astronomy
logic of its own.

- **Standalone 2D/3D UI** — runs on its own, no host required.
- **Catalog search** — query objects/regions through the core.
- **Object inspection** — view an object's attributes and provenance.
- **Navigator control** — drive `unav_core.navigation` (pose, target, FOV).
- **Routes / missions** — build and replay routes and missions.
- **Map / space view** — the 2D map and 3D space viewport.

Sub-packages: `desktop` (shell/lifecycle/windowing), `viewport` (2D map / 3D
space view), `ui` (search, inspection and control views). *Not implemented yet.*

---

## UNAV Server (`unav_server/`)

Exposes the core over a local boundary for the app and for adapters. A thin
transport/orchestration layer — **no astronomy logic**.

- **Local API** — serve core capabilities (search, objects, navigation,
  export) to local clients.
- **Future WebSocket / state sync** — stream real-time navigation state so
  multiple clients (app + adapters) stay in sync.
- **Adapter communication** — the endpoint DCC adapters connect to.

FastAPI/uvicorn are *optional* dependencies (the `server` extra). *Not
implemented yet.*

---

## Adapters (`adapters/`)

DCC integrations, layered on top as **clients**:

- **Cinema 4D** — the *first* adapter (future), never the core.
- **Blender / Houdini / Unreal** — later.
- Adapters **consume** interchange payloads / call the local API and translate
  navigation state into their host's scene. They **do not** own astronomy logic
  and must not require heavy scientific dependencies inside the host runtime.

See [`DCC_ADAPTER_STRATEGY.md`](DCC_ADAPTER_STRATEGY.md).

---

## Dependency isolation rules

| Environment | May depend on |
| --- | --- |
| `unav_core` | astropy, numpy, pydantic, SQLAlchemy; optionally astroquery, pyvo |
| `unav_app` | `unav_core` + a UI/visualisation stack |
| `unav_server` | `unav_core` + (optional) FastAPI/uvicorn |
| `adapters/*` | the host DCC API + a thin UNAV client; **no** heavy science libs |

This table is the contract that keeps Cinema 4D (and friends) free of astropy.

## Supporting directories

- `tools/` — developer and operational tooling.
- `tests/` — the test suite (currently import smoke tests).
- `samples/` — small, curated example data and configs (no bulk data).
- `docs/` — these design documents.

## Current status

This milestone delivers the **architecture and skeleton** only: package
boundaries, documentation and project scaffolding. Data fetching, the UI and the
Cinema 4D adapter are intentionally **not** implemented yet — see
[`ROADMAP.md`](ROADMAP.md).
