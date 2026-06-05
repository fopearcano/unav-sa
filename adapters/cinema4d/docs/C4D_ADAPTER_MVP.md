# Cinema 4D Adapter — MVP

The **first thin** Cinema 4D adapter: connect to a running UNAV-SA server, pull a
mission's camera path, build a camera rig and bake it to the C4D timeline. That is
the whole MVP. **No C4D code is written in this phase** — this fixes the scope,
the API it uses, and the workflow so a later implementation is unambiguous.

> Builds on the broader design in [`C4D_ADAPTER_PLAN.md`](C4D_ADAPTER_PLAN.md);
> the wire protocol is [`C4D_LOCAL_API_PROTOCOL.md`](C4D_LOCAL_API_PROTOCOL.md);
> the boundary rules are [`C4D_DATA_OWNERSHIP_RULES.md`](C4D_DATA_OWNERSHIP_RULES.md).
> UNAV-SA is the standalone application; Cinema 4D is a **client** on top of it.

## Why an MVP first

The MVP proves the **bridge** — that an artist can drive a Cinema 4D camera from a
voyage planned in UNAV-SA — with the least possible code in Cinema 4D's runtime.
It deliberately leaves out point clouds, live sync and round-tripping beyond the
camera. Getting *one* mission onto the timeline validates the architecture: the
science stays in UNAV; Cinema 4D only maps results to scene objects.

## What the MVP adapter CAN do

1. **Connect to the local UNAV server** — configurable host/port (default
   `127.0.0.1:8765`); gate every action on `GET /health`.
2. **Fetch the navigator state** — `GET /navigator/state` to build/refresh the
   camera rig.
3. **Send the active C4D camera state** — read the C4D camera transform,
   inverse-map it, and `POST /navigator/state` (so navigation done in C4D updates
   UNAV).
4. **Import a selected route/mission camera path** — list with `GET /routes` /
   `GET /missions`, then read the chosen mission's camera path (from
   `GET /missions/{id}`; see the protocol's `camera-path` convenience).
5. **Bake the camera path to the C4D timeline** — key each mission segment's camera
   at its computed frame time (segment durations × document FPS) and let C4D
   interpolate.
6. **Optionally create lightweight waypoint/null helpers** — named nulls at the
   route's waypoint positions, grouped under the route (annotation only).

## What the MVP adapter MUST NOT do

(Hard rules — see [`C4D_DATA_OWNERSHIP_RULES.md`](C4D_DATA_OWNERSHIP_RULES.md).)

- **No Astropy** (or any coordinate/time/unit science) in Cinema 4D's runtime.
- **No Gaia/SDSS/DESI/JPL fetching** — no `astroquery`, no archive calls.
- **No database** — no SQLAlchemy/SQLite; the cache lives server-side.
- **No heavy visible-sector rendering** — the MVP does **not** build point clouds;
  it is a camera/mission bridge. (Point clouds are a later phase.)
- **It must not become the core application** — no business logic, no astronomy,
  no data ownership. The adapter maps what the API returns.

## API surface (MVP)

Only a thin slice of the local API, all stdlib HTTP/JSON
([`C4D_LOCAL_API_PROTOCOL.md`](C4D_LOCAL_API_PROTOCOL.md)):

| Action | Endpoint | Status |
| --- | --- | --- |
| Connect / health | `GET /health` | exists |
| Read navigator camera | `GET /navigator/state` | exists |
| Push C4D camera → UNAV | `POST /navigator/state` | exists |
| List routes | `GET /routes` | exists |
| List missions | `GET /missions` | exists |
| Read one mission (camera path source) | `GET /missions/{id}` | exists |
| Camera path (convenience) | `GET /missions/{id}/camera-path` | **proposed** |
| Export camera state (namespaced) | `POST /adapters/cinema4d/export-camera-state` | **proposed, optional** |

The two **proposed** endpoints are conveniences; the MVP works **today** by
deriving the camera path from `GET /missions/{id}` and pushing the camera with
`POST /navigator/state` (the protocol doc gives both the derivation and the
fallback).

## First workflow

```
 UNAV-SA app/server (running)            Cinema 4D + adapter plugin
 ────────────────────────────           ──────────────────────────
   1. artist runs UNAV-SA, plans/loads a mission
                                         2. artist opens the C4D plugin
        GET /health  ◀───────────────── 3. plugin connects to localhost (health gate)
        GET /missions ◀───────────────── 4. artist selects a mission in the plugin
        GET /missions/{id} ◀──────────── 5. plugin pulls the mission's camera path
                                         6. plugin builds a camera rig (null + camera)
                                         7. plugin bakes segment cameras to keyframes
        POST /navigator/state ◀───────── 8. (optional) artist nudges the C4D camera,
                                            plugin pushes it back to UNAV
```

1. The artist **runs the UNAV-SA app/server** and builds or opens a mission
   (see [`../../../docs/VOYAGE_PLANNING_MVP.md`](../../../docs/VOYAGE_PLANNING_MVP.md)).
2. The artist **opens the C4D plugin** (a dialog with host/port + Connect).
3. The plugin **connects to localhost** and health-checks the server.
4. The artist **selects a mission** from the fetched list.
5. The plugin **pulls the mission's camera path**.
6. The plugin **creates a camera rig** — a `UNAV Navigator` null containing a
   `Camera` (and a target null), mapped from the navigator state.
7. The plugin **bakes the timeline** — one keyframe per segment camera at its
   frame time; C4D interpolates between them.
8. *(Optional)* the artist orbits the C4D camera; the plugin **sends it back** to
   UNAV with `POST /navigator/state`.

## Camera rig & baking (summary)

- **Coordinate/units mapping** is the adapter's responsibility (UNAV ICRS parsecs,
  right-handed → C4D units, left-handed, Y-up). The recommended default mapping
  and the inverse are specified in
  [`C4D_ADAPTER_PLAN.md`](C4D_ADAPTER_PLAN.md#coordinate--units-mapping) — the MVP
  reuses it; it does **not** invent new astronomy.
- **Rig:** prefer a look-at rig (camera + target null at `position + direction`)
  over hand-rolled Euler angles; map `fov_degrees` / clip planes where sensible.
- **Baking:** linear key interpolation matches UNAV's deterministic mission
  playback most closely ([`../../../docs/MISSIONS.md`](../../../docs/MISSIONS.md)).
  The adapter keys the **segment** cameras only; it does not re-implement playback.

## Explicitly deferred (not in the MVP)

- Visible-sector **point clouds** in the scene (the heavy render path).
- **Per-object inspection** / metadata in C4D.
- **Round-trip** beyond pushing the camera (focus, re-query loops).
- **Route/label** import beyond optional plain nulls.
- **File-export fallback** and **WebSocket** live sync (see the full plan/protocol).

## Runtime constraints

The adapter targets Cinema 4D's **bundled** Python (often sandboxed, no `pip`), so
it uses the **C4D SDK + the Python standard library only** (`urllib.request`,
`json`, `math`). The HTTP/JSON contract — not a shared Python package — is the
boundary. No `requests`/`numpy`/`pydantic`/`sqlalchemy`.

## MVP "done" criteria (for the future implementation)

- Connect + health from inside Cinema 4D against a running UNAV server.
- Select a mission and build a camera rig from its navigator states.
- Bake the segment cameras to the timeline; scrubbing plays the voyage.
- Push the C4D camera back to UNAV (`POST /navigator/state`) and see it reflected.
- **Zero** astronomy/DB/fetch code in the C4D runtime; stdlib + `c4d` only.
