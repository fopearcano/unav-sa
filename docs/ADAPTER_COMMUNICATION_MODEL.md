# UNAV-SA — Adapter Communication Model

How DCC adapters (Cinema 4D first, then Blender/Houdini/Unreal) talk to UNAV-SA.
This refines [`DCC_ADAPTER_STRATEGY.md`](DCC_ADAPTER_STRATEGY.md) now that the
local API exists.

> **Adapters are clients, not owners of astronomy logic.** They call the local
> API (or consume exported interchange) and map results into the host scene.

## The boundary

```
unav_core  ──►  unav_server (local HTTP API)  ──►  adapter (inside the DCC)  ──►  host scene
   (all the science)        (thin transport)        (thin client, no science deps)
```

An adapter is a small package that:

1. **speaks the local API** over HTTP (localhost) — see
   [`API_ENDPOINTS.md`](API_ENDPOINTS.md); and
2. **maps results into host objects** (nulls/points/cameras/splines), using only
   the host's own SDK.

It must **not** import astropy, numpy-heavy stacks, astroquery or SQLAlchemy. All
of that stays server-side. The API speaks plain JSON, so the adapter needs only
an HTTP client.

## Typical adapter flow

1. `GET /health` — confirm the server is up.
2. `GET /objects/search` / `GET /objects/{uid}` — find targets.
3. `POST /navigator/state` or `POST /navigator/focus/{uid}` — drive the camera;
   the server's `NavigatorState` is the **single source of truth**.
4. `POST /visible-sector/query` — get the objects to instantiate in the host
   scene (each `CatalogObject` carries `x/y/z` in parsecs).
5. `GET /routes` / `GET /missions` — read voyages to drive host animation.

The adapter reflects state; it never recomputes it.

## Data the adapter receives

- **`CatalogObject`** — identity, position (sky and/or Cartesian pc), photometry,
  metadata and provenance. Cartesian `x/y/z` map directly to host scene
  coordinates (the adapter chooses scale/handedness/up-axis — that mapping is the
  adapter's job, not the core's; see [`COORDINATE_CONVENTIONS.md`](COORDINATE_CONVENTIONS.md)).
- **`NavigatorState`** — camera pose + viewing parameters to mirror onto a host
  camera.
- **`Route` / `Mission`** — waypoints, timing and per-waypoint cameras for host
  animation (mission playback is deterministic — see [`MISSIONS.md`](MISSIONS.md)).

## Now vs. future

- **Now:** request/response over the local HTTP API; offline interchange via the
  JSON serialisation of objects, routes, missions and navigator state.
- **Future:** a WebSocket channel for **real-time state sync** so the host camera
  follows live navigation. It will carry the same navigation events
  (`unav_core.navigation.events`) — the event model is already defined.

## Why this keeps hosts safe

Heavy, version-locked scientific dependencies never enter the fragile DCC Python
runtime. Every host reads the same API and therefore shows identical, correct
data — one source of truth, many thin clients.
