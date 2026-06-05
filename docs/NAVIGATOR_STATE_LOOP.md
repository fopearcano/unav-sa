# UNAV-SA — Navigator State Loop

How the standalone UI controls a **single, authoritative navigator state** on the
backend and queries objects from it. The server owns the
[`NavigatorState`](NAVIGATION_STATE.md); the UI is a viewer/editor that mutates it
through the API and reads the result back, so the two never drift.

> Frontend: `unav_app/static/app.js`. Backend: `unav_server` over
> `unav_core.navigation`. Refresh semantics live in
> [`VISIBLE_SECTOR_REFRESH_MODEL.md`](VISIBLE_SECTOR_REFRESH_MODEL.md).

## The state

The backend keeps one `NavigatorState` (in `StateService`). Every field is
persisted and round-trips through the API:

| Field | Meaning |
| --- | --- |
| `position` | camera position `Vec3` (parsecs) |
| `direction` | view direction `Vec3` |
| `up` | up vector `Vec3` |
| `fov_degrees` | field of view |
| `near_distance` / `far_distance` | visible-sector clip range (pc) |
| `cone_angle_degrees` | visible-sector cone half-angle |
| `epoch` | reference epoch (e.g. `J2016.0`), optional |
| `max_visible_objects` | hard cap on a visible-sector result |
| `active_dataset_ids` | advisory active datasets |

## The loop

```
        ┌──────────────── UI (app.js) ────────────────┐
        │  form · movement · focus · sync · reset      │
        └───────────────────┬──────────────────────────┘
            mutate (persist) │                ▲ refresh form from response
                             ▼                │
   POST /navigator/state | /navigator/move | /navigator/focus/{uid}
                             │
                             ▼
                 StateService.state  ◀── the single source of truth
                             │
   POST /visible-sector/query-current  (manual refresh, uses current state)
                             │
                             ▼
        lightweight render objects → 3D points + 2D sky + count
```

Every mutation returns the updated `NavigatorState`; the UI applies it back to the
form (and a read-only state readout), so **what the UI shows always equals what
the backend holds**. The visible sector is then refreshed *from* that state.

## Endpoints

| Method | Path | Body | Effect |
| --- | --- | --- | --- |
| GET | `/navigator/state` | — | read the current state |
| POST | `/navigator/state` | `NavigatorState` | replace the state (persisted) |
| POST | `/navigator/move` | `{direction, distance?}` | step the camera; orientation + view params preserved |
| POST | `/navigator/focus/{uid}` | query `distance?` | aim at an object (and sit `distance` pc away) |
| POST | `/visible-sector/query-current` | — | query the visible sector from the **current** state |

`GET /visible-sector/current/render` (adapter, `points`) and
`POST /visible-sector/query` (explicit state) remain available; the app's loop
uses `query-current`.

## Movement model

`POST /navigator/move` takes a **camera-relative** `direction` and a `distance`
(parsecs, default 10). Only the position changes — orientation (`direction`/`up`)
and the viewing parameters (fov/clip/cone/cap/epoch) are preserved.

| `direction` | moves along |
| --- | --- |
| `forward` / `back` | `±` view direction |
| `right` / `left` | `±` camera right (`forward × up`) |
| `up` / `down` | `±` camera up |

Unknown directions are rejected (`422`); `distance` must be `> 0` (`422`).

## UI controls

- **Navigator state form** — edit position, direction, near/far, fov, cone, max,
  epoch. **Set state** persists it; a read-only line shows the full state
  (including `up`).
- **Movement bar** — `forward/back/left/right/up/down` with a **step (pc)** input
  → `POST /navigator/move`.
- **Focus selected** — `POST /navigator/focus/{uid}` aims the navigator at the
  selected object.
- **Sync navigator to view** — read the 3D orbit camera pose →
  `POST /navigator/state` (navigate by orbiting in 3D, then sync).
- **Reset navigator** — persist a default state and reframe the 3D view.
- **Query visible sector** — the manual refresh: persist the form, then
  `POST /visible-sector/query-current` and render the result + count.

## Consistency & safety

- **Single source of truth.** All mutations go through the backend and the UI
  re-applies the returned state. The `up` vector and other non-form fields are
  carried across edits so they are never silently dropped.
- **Manual refresh.** Movement / focus / sync / reset change the state but do
  **not** auto-query the visible sector — the user clicks **Query visible sector**
  to refresh. There is no per-frame or per-move requery loop. See
  [`VISIBLE_SECTOR_REFRESH_MODEL.md`](VISIBLE_SECTOR_REFRESH_MODEL.md).
- **Cap obeyed.** A query returns at most `max_visible_objects` and flags
  `capped` when the cap limited the result.

## Tests

`tests/test_navigator_state_loop.py` — state get/post round-trip and full-field
persistence, the six move directions (+ accumulation, preserved view params,
default distance, validation), focus persistence/aim, and `query-current`
(reflects the current state, lightweight shape, cap). Plus
`tests/test_navigation_state.py` (model-level) and `tests/test_camera_model.py`.
