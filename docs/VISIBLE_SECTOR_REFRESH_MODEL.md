# UNAV-SA — Visible-Sector Refresh Model

When and how the visible sector is (re)computed, and why it is a **manual,
bounded** action rather than a continuous loop. This keeps the app responsive and
the local database queried only when the user asks.

> Backend: `unav_server` + `unav_core.navigation.visible_sector`. Drives the
> navigator state loop ([`NAVIGATOR_STATE_LOOP.md`](NAVIGATOR_STATE_LOOP.md)) and
> consumes the render payload ([`RENDER_PAYLOAD.md`](RENDER_PAYLOAD.md)).

## Principle: manual refresh, not a frame loop

The visible sector is recomputed **only on an explicit user action** — clicking
**Query visible sector**. Specifically:

- Moving the navigator (`/navigator/move`), focusing
  (`/navigator/focus/{uid}`), syncing from the 3D camera, editing the form, or
  resetting **changes the state but does not query**. The UI shows a hint
  (“… — click *Query visible sector* to refresh”).
- Orbiting / panning / zooming the 3D camera, or panning/zooming the 2D sky,
  issues **no** API calls — it only moves the local view.
- The 3D render loop (`requestAnimationFrame`) just redraws the existing points;
  it never re-queries.
- On page load the sector is **not** auto-queried — the first refresh is manual.

There is therefore **no uncontrolled query loop**: one user click → one query.

## What a refresh does

`POST /visible-sector/query-current` (no body) queries the sector from the
server's **current** `NavigatorState`:

1. resolve candidates within `far_distance` of `position` (indexed Cartesian box);
2. keep those in `[near_distance, far_distance]`;
3. keep those within `cone_angle_degrees` of `direction`;
4. apply optional type / magnitude filters;
5. sort (distance or magnitude) and **cap to `max_visible_objects`**;
6. map to lightweight render objects (no metadata/provenance).

The response is a `VisibleSectorResponse`:

```json
{ "count": 5, "capped": true, "max_visible_objects": 5, "objects": [ … ] }
```

The UI renders `objects` into the 3D points and the 2D sky, and shows the
**count** and a **cap warning** when `capped` is true.

## Obeying `max_visible_objects`

The cap is enforced in `unav_core.navigation.visible_sector.visible_objects`
(`visible[: state.max_visible_objects]`), so **no** query can return more than the
state allows — protecting the payload size and the viewport. `capped` is set when
`count == max_visible_objects` (the conventional “you may have hit the limit”
signal); raise `max` and refresh to see more. See
[`RENDER_PAYLOAD.md`](RENDER_PAYLOAD.md).

## Endpoint choices

| Endpoint | State | Response | Use |
| --- | --- | --- | --- |
| `POST /visible-sector/query-current` | **current** (persisted) | `VisibleSectorResponse` | the app's refresh |
| `POST /visible-sector/query` | body `state` (or current) | `VisibleSectorResponse` | query an explicit pose |
| `GET /visible-sector/current/render` | current | `RenderPayload` (`points`) | adapters |
| `POST /visible-sector/render` | body `state` | `RenderPayload` (`points`) | adapters (chosen pose) |

The app uses **query-current** so a refresh always reflects the authoritative
state. (It first persists the form, so the on-screen state and the queried state
match.)

## Why not auto-refresh?

- **Cost.** Each query hits the local database and rebuilds a payload; doing that
  every frame (or every camera nudge) is wasteful and janky.
- **Predictability.** Navigation (orbit/move) stays smooth and local; data only
  changes when the user commits to a new vantage and asks for it.
- **Determinism in tests.** A refresh is a single, inspectable call.

A future “live” mode could debounce-refresh on movement, but the foundation is
deliberately manual.

## Performance

- Cap with `max_visible_objects` (default 1000); the viewport targets ~10k points.
- The payload is lightweight; full records load per-object via `GET /objects/{uid}`
  only on selection.
- Bound the working set with `far_distance` and `cone_angle_degrees`.

## Tests

`tests/test_navigator_state_loop.py` covers `query-current` (reflects the current
state, obeys the cap, lightweight shape); `tests/test_visible_sector.py` covers
the core filtering/cap; `tests/test_api_visible_sector.py` covers the payload and
cap flag.
