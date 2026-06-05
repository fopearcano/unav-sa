# Cinema 4D Adapter — Limitations (skeleton)

What the **skeleton** adapter does and, honestly, what it does **not** do yet.
This is the first thin client (impl-10); it proves the bridge, not a finished
tool. Scope: [`C4D_ADAPTER_MVP.md`](C4D_ADAPTER_MVP.md). Boundary rules:
[`C4D_DATA_OWNERSHIP_RULES.md`](C4D_DATA_OWNERSHIP_RULES.md).

## What works (skeleton level)

- **Connect + health** against a running UNAV-SA server (`GET /health`).
- **List missions** (`GET /missions`) and pick one.
- **Camera path** for a mission: tries `GET /missions/{id}/camera-path` and, when
  that convenience is absent, **derives** it from `GET /missions/{id}`.
- **Build a camera rig** — `UNAV_CameraRig` null + `UNAV_Camera` + `UNAV_Waypoints`
  nulls at the waypoint positions.
- **Bake** position keyframes (and rotation where a direction is available).
- **Push** the active C4D camera back via `POST /navigator/state`.
- **Stdlib only** in C4D — no astronomy, no DB, no catalog fetching, no heavy deps.

## Known limitations

1. **Position-first baking.** Missions planned in the UNAV-SA UI carry waypoints
   with positions but **no per-segment camera pose**. The adapter therefore bakes
   the **camera position** from each waypoint and adds **rotation** only when a
   segment provides a `camera.direction`. Full per-waypoint camera authoring
   (orientation/FOV per stop) is a later phase.
2. **Camera-path endpoint is derived.** `GET /missions/{id}/camera-path` is a
   *proposed* server convenience; today the client computes the path locally from
   the mission. Output is equivalent; a future server endpoint can replace the
   derivation transparently.
3. **Fixed coordinate scale.** The default mapping is 1 C4D unit = 1 parsec
   (`client.DEFAULT_SCALE`). Galactic distances are large and Solar-System
   positions are tiny in parsecs (see
   [`../../../docs/EPOCH_OBJECTS.md`](../../../docs/EPOCH_OBJECTS.md)); a per-scene
   scale / unit preset is not exposed in the UI yet.
4. **Orientation is basic.** Rotation uses `c4d.utils.VectorToHPB` on the mapped
   direction; bank from the `up` vector and a proper look-at target rig are not
   implemented yet. Interpolation is linear (≈ UNAV playback), not exact-sampled.
5. **Synchronous HTTP on the main thread.** Requests use short timeouts but are
   not yet off-loaded to a worker thread; a slow/large response could briefly
   block the dialog. (The protocol calls for off-thread I/O later.)
6. **No re-import diffing.** Re-importing a mission creates a new
   `UNAV_CameraRig`; it does not update or de-duplicate an existing one.
7. **Placeholder plugin id.** `PLUGIN_ID = 1000001` is development-only — register
   a unique id before release.

## Explicitly out of scope (by design, this phase)

- **Visible-sector point clouds** in the scene (the heavy render path).
- **Per-object inspection / metadata** inside C4D.
- **Round-trip beyond the camera push** (focus, re-query loops).
- **Route/label import** beyond plain waypoint nulls.
- **File-export fallback** and **WebSocket** live sync — see
  [`C4D_API_CLIENT_PROTOCOL.md`](C4D_API_CLIENT_PROTOCOL.md).

## Not bugs — boundary guarantees

These are intentional and must stay true (see the ownership rules):

- The adapter **never** runs Astropy, fetches catalogs, or opens a database.
- All coordinates arrive from the API already in UNAV units; the adapter only
  applies its scene mapping — it computes no astronomy.
- The adapter imports **only** `c4d` + the Python standard library. If a feature
  seems to need more, add it to UNAV-SA and expose it over the API instead.

## Testing note

The pure client (HTTP/JSON, camera-path derivation, coordinate mapping, error
handling) is unit-tested in `tests/test_c4d_adapter_client.py` and exercised
against a live server. The `c4d`-dependent modules (`ui`, `camera_import`,
`timeline_bake`, the `.pyp`) run only inside Cinema 4D and are verified there via
the [manual test checklist](INSTALL_C4D_ADAPTER.md#manual-test-checklist); their
imports are statically checked to contain no heavy dependencies.
