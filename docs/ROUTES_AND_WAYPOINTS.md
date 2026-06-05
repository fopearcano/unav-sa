# UNAV-SA — Routes & Waypoints

`unav_core.routes` models **routes** — ordered, editable paths through space —
and the typed **waypoints** that make them up. Everything is pure, serialisable
data: no DB, no Astropy, no UI. Waypoints reference targets by `uid` and cache a
Cartesian position (`Vec3`, parsecs) for analytics.

> Phase 8 scope. Coordinates are the same Cartesian parsec space as
> `CatalogObject.x/y/z` (see [`COORDINATE_CONVENTIONS.md`](COORDINATE_CONVENTIONS.md)).

## Waypoint kinds

`WaypointKind`: `catalog_object`, `coordinate`, `bookmark`, `annotation_only`,
`custom`. Each kind has a required field (enforced on construction):

| Kind | Requires | Constructor |
| --- | --- | --- |
| `catalog_object` | `object_uid` | `Waypoint.from_object(obj)` |
| `coordinate` | `position` | `Waypoint.from_coordinate(Vec3.of(...))` |
| `bookmark` | `bookmark_id` | `Waypoint.from_bookmark(bookmark)` |
| `annotation_only` | `annotation` or `label` | `Waypoint.annotation_waypoint("note")` |
| `custom` | — | `Waypoint.custom(...)` |

`Waypoint.from_object` caches the object's `uid`, `object_type`, `source` and (if
present) Cartesian `position`, so analytics work without a live DB. Each waypoint
has a stable `wid` (auto-generated) used for editing.

## Route

```python
from unav_core.routes import Route, Waypoint
from unav_core.navigation import Vec3

route = Route(name="Local tour")
route.add_waypoint(Waypoint.from_object(some_star))
route.add_waypoint(Waypoint.from_coordinate(Vec3.of(0, 0, 10), label="midpoint"))
```

Editing (mutates in place):

- `add_waypoint(wp, index=None)` — append or insert.
- `remove_waypoint(wid)` — remove by id (raises `KeyError` if missing).
- `move_waypoint(wid, new_index)` — reposition one waypoint.
- `reorder(order)` — reorder to a permutation of the existing ids.
- `get_waypoint(wid)`, `len(route)`.

## Analytics (`unav_core.routes.analytics`)

- `route.distance_summary()` → `RouteDistanceSummary` (`total_distance_pc`,
  `leg_count`, `positioned_waypoints`, `leg_distances_pc`). Legs connect
  consecutive **positioned** waypoints in order; waypoints without a position
  (e.g. annotation-only) are skipped.
- `route.source_summary()` → `{source: count}` over waypoints with a source.
- `route.object_type_summary()` → `{object_type: count}` over typed waypoints.

## Serialization

`route.to_json()` / `Route.from_json(text)` round-trip a route (and all its
waypoints, including `Vec3` positions and `ObjectType`) through JSON.
