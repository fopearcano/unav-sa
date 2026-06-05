# UNAV-SA — Navigation Engine

`unav_core.navigation` is the DCC-independent, real-time navigation core: where
the navigator is, where it looks, what it can see, and the events that announce
changes. It owns no rendering and talks to no host (per
[`UNAV_SA_ARCHITECTURE.md`](UNAV_SA_ARCHITECTURE.md)).

> Phase 7 scope: state, camera, visible-sector filtering, the event model and the
> route-event foundation.

## Pieces

| Module | Contents |
| --- | --- |
| `vector` | `Vec3` — a tiny immutable 3D vector (pure Python). |
| `camera` | `Camera` — live pose controller (`look_at`, `move_*`, `orbit_target`, `focus_object`). |
| `state` | `NavigatorState` — the serialisable navigation state. |
| `filters` | pure distance/cone/type/magnitude predicates. |
| `visible_sector` | `visible_objects(db, state, ...)` — the visible-sector query. |
| `events` | the event model + a synchronous `EventBus`. |

## The loop

```
            move / aim                       recompute
 Camera ───────────────▶ NavigatorState ───────────────▶ visible_objects(db, state)
   ▲                          │                                  │
   └──── from_camera/to_camera ┘            emit VisibleSectorChangedEvent on change
```

A typical real-time step:

```python
from unav_core.navigation import Camera, NavigatorState, Vec3, visible_objects, EventBus
from unav_core.db import Database

bus = EventBus()
cam = Camera(position=Vec3.of(0, 0, 0))
cam.move_forward(10)
state = NavigatorState.from_camera(cam, far_distance=200, cone_angle_degrees=40)
visible = visible_objects(Database("data/unav.db"), state)   # sorted, capped
```

## Dependency boundaries

- **Pose/state/events are dependency-light** — `Vec3`, `Camera`, `NavigatorState`
  and the event model use only pydantic + stdlib `math`. They pull **no**
  SQLAlchemy and **no** Astropy, so a DCC **adapter** can consume a serialised
  `NavigatorState` without the database/science stack.
- **`visible_objects` needs the local cache** (`unav_core.db`), so it is imported
  lazily from the package root (`from unav_core.navigation import visible_objects`).
- Navigation never imports the app, server or adapters.

## Event model

Five typed events (`unav_core.navigation.events`):

| Event | Meaning |
| --- | --- |
| `NavigationMovedEvent` | position/direction changed |
| `VisibleSectorChangedEvent` | the visible-object set changed |
| `DatasetChangedEvent` | active dataset selection changed |
| `ObjectSelectedEvent` | an object was selected |
| `RouteChangedEvent` | the active route changed (route foundation) |

`EventBus` is a minimal synchronous dispatcher (`subscribe`, `subscribe_type`,
`emit`) — the foundation for the App's reactivity and the future server-side
state sync; transport (WebSocket, etc.) is a later concern.

## Known limitation: `active_dataset_ids`

`NavigatorState.active_dataset_ids` is carried in state and announced via
`DatasetChangedEvent`, but `visible_objects` does **not** yet filter by dataset:
the `objects` table does not link rows to datasets (Phase 3 schema). Dataset-scoped
visibility is future work (a dataset link on `objects`, or an in-memory working
set). It is documented here rather than silently ignored.
