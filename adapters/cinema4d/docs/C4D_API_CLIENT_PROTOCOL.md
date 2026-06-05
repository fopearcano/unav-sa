# Cinema 4D Adapter — API Client Protocol

How the future C4D adapter communicates with UNAV-SA. **Planning only.** Three
mechanisms, in priority order:

1. **HTTP local API — first/primary.**
2. **File-export interchange — fallback** (offline / server unreachable).
3. **WebSocket state-sync — future/optional.**

See the server reference:
[`../../../docs/LOCAL_API_SERVER.md`](../../../docs/LOCAL_API_SERVER.md),
[`../../../docs/API_ENDPOINTS.md`](../../../docs/API_ENDPOINTS.md),
[`../../../docs/FRONTEND_RENDER_PAYLOAD.md`](../../../docs/FRONTEND_RENDER_PAYLOAD.md).

## Transport rules

- **Stdlib only.** Requests use `urllib.request`; bodies/responses are JSON via
  `json`. **No `requests`, `httpx`, `numpy`, `pydantic`** — they may be unavailable
  in C4D's bundled Python. The HTTP/JSON contract *is* the boundary.
- **Localhost.** Default base URL `http://127.0.0.1:8765`, configurable. The API is
  a local server; do not target untrusted networks.
- **Timeouts + retries.** Short connect/read timeouts; a couple of retries with
  backoff. Network/HTTP work happens off the main thread where the C4D SDK allows,
  to avoid freezing the UI.
- **Content type** `application/json` for POST bodies.

## 1. HTTP local API (primary)

### Connection / health

```
GET /health  ->  {"status": "ok", "object_count": <int>}
```

The adapter pings this on **Connect** and shows the object count. Non-200 or a
connection error → surface "UNAV server not reachable" and offer the file fallback.

### Endpoint → adapter action map

| Adapter action | Endpoint | Notes |
| --- | --- | --- |
| Connect / status | `GET /health` | gate all actions on this. |
| List datasets | `GET /datasets` | informational. |
| Read navigator camera | `GET /navigator/state` | build/refresh the camera rig. |
| Push C4D camera → UNAV | `POST /navigator/state` | body = `NavigatorState`. |
| Focus an object | `POST /navigator/focus/{uid}` | optional `?distance=`. |
| Visible sector (render) | `GET /visible-sector/current/render` | slim points for the current state. |
| Visible sector for a pose | `POST /visible-sector/render` | body `{state, sort?, object_types?, max_magnitude?}`. |
| Inspect one object | `GET /objects/{uid}` | full record, **on selection only**. |
| Search | `GET /objects/search?q=&source=&object_type=&limit=` | find targets. |
| List / read routes | `GET /routes` | waypoint labels. |
| List / read missions | `GET /missions` | camera-path baking. |

The adapter prefers the **render** endpoints (`/visible-sector/.../render`) for
scene building — they return the lightweight payload (render objects with
`uid/name/source/object_type/x/y/z/ra_deg/dec_deg/distance_pc/display_color/display_size`)
with **no** metadata/provenance, so thousands of points stay cheap. Full
`CatalogObject`s are fetched per-object via `GET /objects/{uid}` only when the
artist selects a point. (`POST /visible-sector/query` returns the same render
objects plus a `capped` flag; see [`../../../docs/RENDER_PAYLOAD.md`](../../../docs/RENDER_PAYLOAD.md).)

### Example: build the point cloud

```
GET /visible-sector/current/render
->
{
  "count": 2,
  "points": [
    {"uid":"gaia:1","name":"Vega","source":"Gaia DR3","object_type":"star",
     "x":0.96,"y":-5.9,"z":4.8,"ra_deg":279.2,"dec_deg":38.8,"distance_pc":7.68,
     "display_color":"#cfe8ff","display_size":4.99}
  ]
}
```

The adapter maps each point's `x/y/z` (parsecs, right-handed) into the C4D scene
(see the mapping in [`C4D_ADAPTER_PLAN.md`](C4D_ADAPTER_PLAN.md#coordinate--units-mapping)),
colours by `display_color`, scales by `display_size`.

### Example: push the camera back

```
POST /navigator/state
Content-Type: application/json
{
  "position":  {"x": 0.0, "y": 0.0, "z": 0.0},
  "direction": {"x": 0.0, "y": 0.0, "z": -1.0},
  "up":        {"x": 0.0, "y": 1.0, "z": 0.0},
  "far_distance": 1000.0, "cone_angle_degrees": 45.0
}
->  the stored NavigatorState (echoed)
```

The adapter reads the C4D camera's global matrix, inverse-maps position/direction/up
to UNAV space, and posts them. An invalid state (e.g. zero direction) returns `422`
— surface it; do not silently coerce.

### Missions (camera path)

```
GET /missions  ->  [Mission, ...]
```

A `Mission` carries a `route` and `segments`; each segment has a `camera`
(`NavigatorState`), `transition_seconds` and `hold_seconds`
([`../../../docs/MISSIONS.md`](../../../docs/MISSIONS.md)). The adapter keys each
segment camera at its timeline position (durations × document FPS) and lets C4D
interpolate. (Future: a per-frame mission-sampling endpoint for exact fidelity.)

## 2. File-export interchange (fallback)

When the server is unreachable, or for offline handoff, the adapter reads **JSON
files** UNAV produced — the same serialised models, so no second schema:

| File content | Produced by | Adapter use |
| --- | --- | --- |
| Render points (`RenderPayload` JSON) | UNAV app/CLI export | build the point cloud |
| `NavigatorState` JSON | `model_dump_json()` | camera rig |
| `Route` JSON | `Route.to_json()` | waypoint labels |
| `Mission` JSON | `Mission.to_json()` | bake camera path |
| Catalog `JSONL` | `unav_core.data.io.write_jsonl` | bulk objects |

The adapter parses these with `json` and applies the **same mapping** as the HTTP
path. (A UNAV-side "export for C4D" command may be added so the app can drop these
files; that is a UNAV concern, not the adapter's.)

## 3. WebSocket state-sync (future, optional)

Later, a WebSocket channel can stream the navigation **events**
(`navigation_moved`, `visible_sector_changed`, `object_selected`, …;
`unav_core.navigation.events`) so the C4D camera follows live navigation and
pushes moves back in real time. Not in scope now; the request/response API and
file fallback come first. The event model already exists, so this is additive.

## Error handling summary

| Situation | Adapter behaviour |
| --- | --- |
| Server unreachable | message + offer file fallback; never block the UI. |
| `404` (unknown object) | inform; skip. |
| `400` (bad sort/region) / `422` (invalid state) | surface the detail; fix input. |
| Empty result | inform ("0 points"); do not error. |
| Large payloads | rely on the slim render payload; cap counts via state limits. |

No retries should mutate state more than once (pushes are idempotent on the
server: setting the same `NavigatorState` twice is fine).
