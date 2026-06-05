# UNAV-SA — Missions

`unav_core.missions` turns a [route](ROUTES_AND_WAYPOINTS.md) into a reproducible,
playable voyage: a title/description, per-waypoint **camera settings**, **timing**,
notes and tags. Pure, serialisable data — no DB, no Astropy, no UI.

> Phase 8 scope. Deterministic playback by design.

## Mission & segments

A `Mission` wraps a `Route` and a list of `MissionSegment`s. Each segment pairs a
route waypoint with timing and an optional camera pose
(`NavigatorState` from [`NAVIGATION_STATE.md`](NAVIGATION_STATE.md)):

| Field | Meaning |
| --- | --- |
| `waypoint_id` | the route waypoint this segment plays |
| `camera` | the pose at this waypoint (`NavigatorState`) |
| `transition_seconds` | time to travel *to* this waypoint (the first segment's is ignored) |
| `hold_seconds` | dwell time at this waypoint |
| `note` | optional per-segment note |

`Mission` fields: `title`, `description`, `route`, `segments`, `notes`, `tags`,
`created_at`, `metadata`. `mission.total_duration_seconds` is the timeline length
(holds + transitions, excluding the first segment's transition).

```python
from unav_core.missions import Mission
from unav_core.navigation import NavigatorState, Vec3

cameras = {wp.wid: NavigatorState(position=..., direction=...) for wp in route.waypoints}
mission = Mission.build(route, title="Grand tour", cameras=cameras,
                        transition_seconds=10.0, hold_seconds=2.0)
```

`Mission.build` creates one segment per route waypoint (in order); segments must
reference waypoints that exist in the route (validated).

## Playback (`unav_core.missions.playback`)

The timeline, per segment in order: a **transition** phase that interpolates the
camera from the previous segment's pose to this one's (skipped for the first
segment), then a **hold** phase at this pose.

- `evaluate_at_seconds(mission, t)` — sample at time `t` (clamped to the timeline).
- `evaluate_at_progress(mission, p)` — sample at normalised progress `p ∈ [0, 1]`.

Both return a `PlaybackSample` (`seconds`, `progress`, `segment_index`,
`waypoint_id`, `phase`, `camera`). `phase` is one of `start`, `transition`,
`hold`, `end`.

Playback requires a camera on **every** segment (`mission.has_cameras()`);
otherwise it raises `ValueError`.

### Deterministic interpolation

Interpolation is **linear** and deterministic: `position` and the scalar viewing
fields (`fov`, `near`/`far`, `cone_angle`) are lerped; `direction`/`up` are lerped
then normalised; discrete fields (`epoch`, `max_visible_objects`,
`active_dataset_ids`) snap to the nearer endpoint. The same input always yields
the same sample — suitable for reproducible exports and (future) rendering.

## Serialization

`mission.to_json()` / `Mission.from_json(text)` round-trip the whole mission
(route, segments and cameras) through JSON.
