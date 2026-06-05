# Cinema 4D Adapter — Local API Protocol (MVP)

The exact local API the **MVP** adapter speaks: a thin **camera + mission** bridge
over localhost HTTP/JSON. This is the focused subset for the MVP; the full client
protocol (render payload, file fallback, WebSocket) is in
[`C4D_API_CLIENT_PROTOCOL.md`](C4D_API_CLIENT_PROTOCOL.md). Endpoint reference:
[`../../../docs/API_ENDPOINTS.md`](../../../docs/API_ENDPOINTS.md).

> Planning only — no adapter code yet. Every endpoint below already exists in
> UNAV-SA **except** the two marked **proposed**, for which a working fallback is
> documented.

## Transport rules

- **Stdlib only.** `urllib.request` for HTTP, `json` for bodies/responses. No
  `requests`/`httpx`/`numpy`/`pydantic` — they may be missing in C4D's Python. The
  HTTP/JSON contract *is* the boundary.
- **Localhost.** Base URL defaults to `http://127.0.0.1:8765`, configurable. Do not
  target untrusted networks.
- **Short timeouts + a couple of retries** with backoff; run off the main thread
  where the SDK allows so the UI never freezes.
- **`Content-Type: application/json`** on POST bodies. Reads are idempotent; the
  one write (`POST /navigator/state`) is idempotent server-side (re-posting the
  same state is safe).

## Endpoints (MVP)

| # | Method | Path | Status | Adapter use |
| --- | --- | --- | --- | --- |
| 1 | GET | `/health` | exists | gate every action; show object count |
| 2 | GET | `/navigator/state` | exists | read the navigator camera → build/refresh rig |
| 3 | POST | `/navigator/state` | exists | push the active C4D camera back to UNAV |
| 4 | GET | `/routes` | exists | list routes (optional waypoint nulls) |
| 5 | GET | `/missions` | exists | list missions to choose from |
| 6 | GET | `/missions/{id}` | exists | read a mission → derive its camera path |
| 7 | GET | `/missions/{id}/camera-path` | **proposed** | camera path convenience (see below) |
| 8 | POST | `/adapters/cinema4d/export-camera-state` | **proposed, optional** | namespaced camera push (see below) |

### 1. `GET /health`

```
GET /health  ->  {"status": "ok", "object_count": <int>}
```
On **Connect**: 200 → enable actions and show the count; connection error / non-200
→ "UNAV server not reachable" (do not block the UI).

### 2–3. Navigator state (read / push)

```
GET  /navigator/state  ->  NavigatorState
POST /navigator/state   (body: NavigatorState)  ->  the stored NavigatorState
```
`NavigatorState` carries `position`, `direction`, `up`, `fov_degrees`,
`near_distance`, `far_distance`, `cone_angle_degrees`, `epoch`,
`max_visible_objects` ([`../../../docs/NAVIGATION_STATE.md`](../../../docs/NAVIGATION_STATE.md)).
The adapter maps `position/direction/up` between UNAV (ICRS pc, right-handed) and
C4D (units, left-handed, Y-up) using the mapping in
[`C4D_ADAPTER_PLAN.md`](C4D_ADAPTER_PLAN.md#coordinate--units-mapping). An invalid
state (e.g. zero `direction`) returns `422` — surface it; do not silently coerce.

### 4–6. Routes & missions

```
GET /routes        ->  [Route, ...]
GET /missions      ->  [Mission, ...]
GET /missions/{id} ->  Mission   (404 if unknown)
```
A `Mission` has a `route` and ordered `segments`; each segment has a `camera`
(optional `NavigatorState`), `transition_seconds` and `hold_seconds`
([`../../../docs/MISSIONS.md`](../../../docs/MISSIONS.md)). The mission is the
**source of the camera path** the MVP bakes.

### 7. `GET /missions/{id}/camera-path` (proposed convenience)

A convenience that pre-computes what the adapter would otherwise derive from
`GET /missions/{id}`. Proposed shape:

```
GET /missions/{id}/camera-path?fps=30
->
{
  "mission_id": "…",
  "fps": 30,
  "total_seconds": 20.0,
  "keys": [
    {"index": 0, "waypoint_id": "…", "time_seconds": 0.0,  "frame": 0,
     "camera": { NavigatorState | null }, "hold_seconds": 0.0},
    {"index": 1, "waypoint_id": "…", "time_seconds": 10.0, "frame": 300,
     "camera": { NavigatorState | null }, "hold_seconds": 0.0}
  ]
}
```

**Until it exists, derive it client-side from `GET /missions/{id}`** (this is the
MVP path):

```
t = 0
for i, segment in enumerate(mission.segments):
    if i > 0:
        t += segment.transition_seconds        # first segment's transition is ignored
    key.time_seconds = t
    key.frame        = round(t * fps)
    key.camera       = segment.camera           # a NavigatorState, or null
    t += segment.hold_seconds                   # dwell before the next transition
```

Segments whose `camera` is `null` are skipped for keying (no pose to bake). This
matches UNAV's deterministic playback ([`../../../docs/MISSIONS.md`](../../../docs/MISSIONS.md));
the adapter keys segment cameras and lets C4D interpolate (linear ≈ UNAV).

### 8. `POST /adapters/cinema4d/export-camera-state` (proposed, optional)

A namespaced, adapter-specific convenience for pushing the C4D camera (e.g. with
extra adapter metadata) without overloading `/navigator/state`. Proposed shape:

```
POST /adapters/cinema4d/export-camera-state
{ "state": NavigatorState, "source": "cinema4d", "scale": 1.0 }
->  the stored NavigatorState (echoed)
```

**Until it exists, push with `POST /navigator/state`** (the existing, sufficient
path). The namespaced endpoint is optional sugar for a later phase; it must not
add astronomy logic — it just stores the posted state like `/navigator/state`.

## Error handling (MVP)

| Situation | Adapter behaviour |
| --- | --- |
| Server unreachable | message; offer to retry; never block the UI |
| `404` (unknown mission/object) | inform; skip |
| `422` (invalid navigator state) | surface the detail; fix the input |
| Empty list (`[]`) | inform ("no missions"); not an error |

## Out of scope here (see the full protocol)

The render payload (`/visible-sector/*`), per-object inspection
(`GET /objects/{uid}`), the **file-export fallback** and **WebSocket** live sync
are documented in [`C4D_API_CLIENT_PROTOCOL.md`](C4D_API_CLIENT_PROTOCOL.md) and are
**not** part of the MVP camera/mission bridge.
