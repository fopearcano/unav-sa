# UNAV-SA — Bookmarks, Routes & Missions

The persistent **voyage-planning** data model and its API. Bookmarks, routes and
missions are pure `unav_core` models, stored as JSON in the local SQLite database
so they **survive an app restart**.

> Models: `unav_core.navigation.bookmarks`, `unav_core.routes`,
> `unav_core.missions`. Persistence: `unav_core.db.planning`. API:
> `unav_server.api`. See also [`BOOKMARKS.md`](BOOKMARKS.md),
> [`ROUTES_AND_WAYPOINTS.md`](ROUTES_AND_WAYPOINTS.md), [`MISSIONS.md`](MISSIONS.md)
> and the workflow in [`VOYAGE_PLANNING_MVP.md`](VOYAGE_PLANNING_MVP.md).

## The models

- **Bookmark** — a saved object and/or coordinate with a `label`, `tags`, `notes`.
  References a catalog object by `object_uid` and/or caches a Cartesian `position`
  (parsecs).
- **Waypoint** — one stop in a route: a `catalog_object` (by uid, with a cached
  position), a `coordinate`, a `bookmark`, an `annotation`, or `custom`.
- **Route** — an ordered, editable list of waypoints (`add`/`remove`/`move`/
  `reorder`) with analytics: `distance_summary()` (total + per-leg pc over the
  positioned waypoints), `source_summary()`, `object_type_summary()`.
- **Mission** — a route plus timed `segments` (one per waypoint: optional camera
  `NavigatorState`, `transition_seconds`, `hold_seconds`) — a playable voyage.

## Persistence

Each kind has its own table (`bookmarks`, `routes`, `missions`), storing the
model JSON keyed by id with an insertion `created_at` for stable ordering. `save_*`
is an **upsert** that preserves `created_at` on update (editing a route doesn't
reorder it). Because plans live in the same SQLite file as the catalog, they
persist across restarts. `unav_core.db.planning` exposes
`save_/list_/get_/delete_` for each kind; `StateService` delegates to them.

## API

| Method | Path | Body | Effect |
| --- | --- | --- | --- |
| GET | `/bookmarks` | — | list bookmarks |
| POST | `/bookmarks` | `Bookmark` | create (server caches the object's position if `object_uid` given) |
| DELETE | `/bookmarks/{id}` | — | delete (`204`, `404` if absent) |
| GET | `/routes` | — | list routes |
| POST | `/routes` | `Route` | create |
| GET | `/routes/{id}` | — | read one (`404`) |
| PUT | `/routes/{id}` | `Route` | replace (id from the path) |
| DELETE | `/routes/{id}` | — | delete (`204`/`404`) |
| POST | `/routes/{id}/add-object/{uid}` | — | append a catalog object as a waypoint (`404` if route/object missing) |
| GET | `/routes/{id}/summary` | — | `RouteDistanceSummary` |
| GET | `/missions` | — | list missions |
| POST | `/missions` | `Mission` | create |
| GET | `/missions/{id}` | — | read one (`404`) |
| PUT | `/missions/{id}` | `Mission` | replace |
| DELETE | `/missions/{id}` | — | delete (`204`/`404`) |
| POST | `/missions/{id}/add-route/{route_id}` | — | extend the mission with another route's waypoints (+ a segment each) |

### Notes

- **`add-object`** runs server-side because it needs the object's cached position
  from the DB (so route distances and the 3D path work). The waypoint stores the
  object's `uid`, type, source and `position`.
- **Reorder / remove** waypoints by editing the route client-side and `PUT`ing it
  back (the order is the `waypoints` list order).
- **`add-route`** merges the referenced route's waypoints into the mission's route
  (deduped by waypoint id) and appends a `MissionSegment` for each — so a mission
  can accumulate stops from several routes.
- **Create a mission from a route**: `POST /missions` with `{title, route,
  segments?}` (the UI builds one segment per waypoint).

## Tests

`tests/test_api_voyage.py` — bookmark CRUD + cached position, route build /
add-object / reorder / delete / **distance summary**, mission create-from-route /
add-route, and **persistence across a simulated restart** (two app instances over
one DB file). Model-level coverage lives in `tests/test_bookmarks.py`,
`tests/test_routes.py`, `tests/test_missions.py`.
