# Cinema 4D Adapter — Data Ownership Rules

The boundary contract between UNAV-SA and the Cinema 4D adapter. One sentence:

> **UNAV-SA owns the science and the data; the adapter owns only the Cinema 4D
> scene.**

These rules keep heavy/scientific logic out of Cinema 4D's runtime and keep UNAV
the single source of truth. They apply to the MVP and every later phase. Context:
[`../../../docs/DCC_ADAPTER_STRATEGY.md`](../../../docs/DCC_ADAPTER_STRATEGY.md),
[`../../../docs/PRODUCT_IDENTITY.md`](../../../docs/PRODUCT_IDENTITY.md).

## Who owns what

| Concern | Owner | Notes |
| --- | --- | --- |
| Astronomy (coordinates, time, units, frames) | **UNAV** | Astropy lives only in `unav_core`. |
| Data fetching (Gaia/SDSS/DESI/JPL) | **UNAV** | server-side connectors; `astroquery` never in C4D. |
| Local cache / database | **UNAV** | SQLite lives server-side; the adapter never opens a DB. |
| Catalog records, provenance, validation | **UNAV** | the adapter renders what the API returns. |
| Navigator state (the authority) | **UNAV** | the adapter reads it and can push a new pose. |
| Visible-sector selection / queries | **UNAV** | cone/region/sort/cap all server-side. |
| Mission playback semantics | **UNAV** | the adapter keys segment cameras; it doesn't re-derive playback. |
| Coordinate→scene mapping (handedness, up-axis, scale) | **adapter** | the host mapping is the adapter's choice. |
| Cinema 4D scene objects (camera rig, nulls, keys) | **adapter** | building/animating host objects is the adapter's job. |
| Plugin UI (dialog, host/port, buttons) | **adapter** | a thin client UI only. |

## The adapter MUST NOT

1. **Run Astropy** — no coordinate/time/unit/frame computation in the C4D runtime.
2. **Fetch catalogs** — no Gaia/SDSS/DESI/JPL, no `astroquery`, no archive HTTP.
3. **Own a database** — no SQLAlchemy/SQLite; no reading or writing UNAV's cache.
4. **Do heavy visible-sector rendering** — no cone/region selection, no building
   tens of thousands of scene objects as "the renderer". (Lightweight point clouds,
   when added later, consume the server's render payload — they don't compute it.)
5. **Re-derive astronomy** — no recomputing distances, redshifts, Galactic
   coordinates, validation or provenance.
6. **Mutate UNAV's data** — no importing catalogs, no writing the DB. The only
   write-back is **navigation state** (`POST /navigator/state`).
7. **Become the core application** — no business logic, no being "UNAV inside C4D".
   The adapter is a client; UNAV runs and owns the data with or without Cinema 4D.
8. **Pull heavy Python dependencies into C4D** — no `numpy`/`pydantic`/`requests`/
   `sqlalchemy`. **C4D SDK + stdlib only.**

## The adapter MAY

- **Connect** to the local UNAV server and health-check it.
- **Read** navigator state, routes, missions (and, in later phases, the render
  payload and single-object records).
- **Push** the active C4D camera back as a `NavigatorState`.
- **Map** UNAV positions/orientations into the C4D scene (it **owns** the scale,
  handedness and up-axis mapping — see
  [`C4D_ADAPTER_PLAN.md`](C4D_ADAPTER_PLAN.md#coordinate--units-mapping)).
- **Create** Cinema 4D objects: a camera rig, mission keyframes, and optional
  annotation nulls at waypoint positions.

## The dependency boundary

```
unav_core (Astropy, numpy, pydantic, SQLAlchemy, astroquery*)   ← all heavy deps
        │  *optional
unav_server (FastAPI)        ← thin HTTP/JSON transport
        │  http://127.0.0.1  ← the ONLY contract the adapter sees
C4D adapter (c4d SDK + Python stdlib only)                       ← no heavy deps
        │
Cinema 4D scene
```

The boundary is the **HTTP/JSON API**, not a shared Python package. That is what
guarantees these rules hold: Cinema 4D's interpreter never imports UNAV's
scientific stack, so it *cannot* accidentally take ownership of the science.

## Why these rules

- **Portability** — C4D's bundled Python is often sandboxed (no `pip`); a stdlib
  client runs everywhere, any C4D version.
- **Single source of truth** — coordinates/validation/provenance computed once, in
  UNAV, are identical in the app, the API and every adapter.
- **Identity** — UNAV-SA is a standalone navigator, **not** a Cinema 4D plugin
  (see [`../../../docs/PRODUCT_IDENTITY.md`](../../../docs/PRODUCT_IDENTITY.md)). The
  adapter is a thin client on top, never the core.

## Keeping it honest (for the future implementation)

- The adapter package imports **only** `c4d` and stdlib modules; a contributor
  adding `import numpy` (etc.) is violating rule 8.
- All astronomy enters via API responses already in UNAV units; the adapter only
  applies its scene mapping.
- If the adapter needs a new computation, the rule is: **add it to UNAV and expose
  it over the API**, not to the adapter.
