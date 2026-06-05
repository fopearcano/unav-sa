# Cinema 4D Adapter — Plan

Design for the future Cinema 4D (C4D) adapter. **No C4D code is implemented in
this phase** — this document fixes scope, boundaries and the technical mapping so
implementation is unambiguous later.

Context: [`../../../docs/DCC_ADAPTER_STRATEGY.md`](../../../docs/DCC_ADAPTER_STRATEGY.md),
[`../../../docs/ADAPTER_COMMUNICATION_MODEL.md`](../../../docs/ADAPTER_COMMUNICATION_MODEL.md),
[`../../../docs/LOCAL_API_SERVER.md`](../../../docs/LOCAL_API_SERVER.md).

## Position

```
unav_core (all astronomy/data)  ──►  unav_server (local HTTP API)  ──►  C4D adapter  ──►  C4D scene
        the science                       thin transport               thin client       host objects
```

The adapter is a **client**. It maps UNAV responses onto Cinema 4D objects using
only the C4D SDK. UNAV remains the **single source of truth** for navigation
state, coordinates, queries, validation and provenance.

## Responsibilities (what the adapter DOES)

1. **Connect to the UNAV local server.** Configurable host/port (default
   `127.0.0.1:8765`); a health check (`GET /health`) before acting.
2. **Import a camera path.** From a UNAV **Mission** (route + per-waypoint cameras
   + timing) or the current **NavigatorState** — produce C4D camera keyframes /
   a camera animation.
3. **Create a C4D camera/null rig.** A tidy hierarchy (e.g. a `UNAV Navigator`
   null containing a `CameraObject` and, where useful, a target null) that mirrors
   the UNAV navigator camera.
4. **Create a lightweight visible-sector representation (if needed).** From the
   **render payload** (`uid/x/y/z/display_color/display_size`), build a *single*
   point/cloud representation per object type (not one object per point) — see
   "Visibility".
5. **Bake a mission to the C4D timeline.** Map mission segment cameras to keyframes
   at frame times derived from the segment durations and the document FPS; let
   C4D interpolate between keys.
6. **Send the selected camera position back to UNAV.** Read the C4D camera
   transform, inverse-map it to a UNAV `NavigatorState`, and `POST /navigator/state`
   (or `POST /navigator/focus/{uid}`); then re-query the visible sector.
7. **Import route/waypoint labels.** Map waypoints to named nulls (optionally text
   splines) at their positions, grouped under the route.

## What the adapter MUST NOT do

These are hard rules (from the adapter strategy):

- **No Astropy inside C4D.** No coordinate/time/unit science in the host runtime.
- **No heavy database inside C4D.** No SQLAlchemy/SQLite query engine; the local
  cache lives server-side.
- **No Gaia/SDSS/DESI/JPL fetching inside C4D.** No astroquery, no archive calls;
  data fetching is a server-side connector concern.
- **No ownership of core astronomy logic.** No re-deriving coordinates, distances,
  redshifts, validation or provenance. The adapter renders what the API returns.

Additional constraints (corollaries):

- **No heavy Python dependencies in C4D's interpreter** — no `numpy`, `pydantic`,
  `requests`, `sqlalchemy`, etc. Use **only the C4D SDK + the Python standard
  library** (see "Runtime constraints").
- **No business logic.** Sorting, filtering, cone/region selection, mission
  playback semantics — all stay in UNAV; the adapter only maps results to scene.
- **No writes to the UNAV database.** The adapter reads via the API and pushes
  *navigation state* back; it does not import catalogs or mutate the cache (that
  is the app/CLI's job).

## Runtime constraints (critical)

Cinema 4D ships its **own** bundled Python (Python 3.x in R23+/2023+; older
versions shipped 2.7). That interpreter is often **sandboxed without pip**, so the
adapter must assume it **cannot install packages**.

→ **The adapter depends on the C4D SDK (`c4d`) and the Python standard library
only.** HTTP uses `urllib.request`; parsing uses `json`; maths uses `math`. This
is what keeps heavy science out of the host and makes the adapter portable across
C4D versions. The HTTP/JSON protocol (not a shared Python package) is the boundary.

## Architecture (conceptual — no code yet)

Anticipated modules (names indicative):

| Module | Role |
| --- | --- |
| `api_client` | stdlib HTTP/JSON client for the UNAV endpoints + file fallback. |
| `coordinate_map` | UNAV (ICRS pc, right-handed) ⇄ C4D (units, left-handed, Y-up). |
| `scene/camera_rig` | build/update the camera + null hierarchy. |
| `scene/visibility` | render payload → lightweight point objects (grouped by type). |
| `scene/labels` | waypoints/routes → named nulls / text. |
| `mission_baker` | mission segments → timeline keyframes. |
| `ui` | a C4D dialog (host/port, connect, the action buttons). |

## Coordinate & units mapping

UNAV positions are **ICRS Cartesian, parsecs, right-handed**
(x→RA0/Dec0, y→RA90/Dec0, z→north celestial pole — see
[`../../../docs/COORDINATE_CONVENTIONS.md`](../../../docs/COORDINATE_CONVENTIONS.md)).
Cinema 4D is **left-handed, Y-up**, default unit centimetres.

The adapter **owns** the mapping (scale/handedness/up-axis are the adapter's
choice, per the strategy). Recommended default (configurable):

```
C4D.X = scale * unav.x
C4D.Y = scale * unav.z      # celestial north -> scene "up" (Y)
C4D.Z = scale * unav.y      # the y<->z swap is an odd permutation, so it also
                            # converts right-handed -> left-handed (no extra mirror)
```

- `scale` is **C4D units per parsec** (configurable; e.g. 1 unit = 1 pc). Parsec
  distances are large; the scale keeps scenes workable.
- The inverse (for pushing the camera back): `unav.(x,y,z) = (C4D.X, C4D.Z,
  C4D.Y) / scale`. Direction/up vectors use the same swap **without** the scale,
  then are normalised.
- Camera orientation: prefer a **look-at** rig (camera + target null at
  `position + direction`) over hand-rolled HPB Euler angles; derive bank from the
  `up` vector. UNAV `NavigatorState` carries `position`, `direction`, `up`,
  `fov_degrees`, `near_distance`, `far_distance` (see
  [`../../../docs/NAVIGATION_STATE.md`](../../../docs/NAVIGATION_STATE.md)); map FOV
  and clip planes to the C4D camera where sensible.

## Visibility representation

The render payload targets ≥10k points
([`../../../docs/FRONTEND_RENDER_PAYLOAD.md`](../../../docs/FRONTEND_RENDER_PAYLOAD.md)).
**Do not create one C4D object per point.** Recommended: one point/cloud object
**per object type** (a handful of objects), each coloured with the payload colour,
vertices = the points of that type. This stays lightweight, gives colour-by-type,
and avoids exploding the object manager. (A MoGraph cloner driven by a point list
is an alternative.) Per-object metadata is fetched **only on selection**
(`GET /objects/{uid}`), never for all points.

## Mission baking fidelity

UNAV mission playback is deterministic linear interpolation
([`../../../docs/MISSIONS.md`](../../../docs/MISSIONS.md)). The adapter will key the
**segment** cameras at their computed timeline positions and let C4D's F-curves
interpolate between them (set linear interpolation for closest match). For
exact-fidelity baking, UNAV may later expose a **mission-sampling** endpoint
(per-frame `NavigatorState`); until then, segment-key baking is the plan — the
adapter does **not** re-implement playback maths.

## Phasing (future implementation, not now)

1. **Connect & read** — health check; pull current state + render payload; build
   the camera rig and a static point cloud (read-only).
2. **Missions** — pull a mission; bake camera keyframes to the timeline.
3. **Round-trip** — push the C4D camera back to UNAV; re-query the sector.
4. **Labels & routes** — waypoint nulls / text; route grouping.
5. **File fallback** — import exported JSON when the server is unreachable.
6. **(Optional, later)** WebSocket live state-sync.

## Open questions (to resolve before coding)

- C4D version target (Python 3.9+/3.11 in recent releases) and minimum supported.
- Default `scale` and whether to expose presets (pc/ly/AU display scales).
- Point rendering choice (point object vs. cloner vs. instances) per performance.
- Whether labels should be C4D text objects (MoText) or annotation nulls by default.
