# UNAV-SA — Voyage Planning MVP

Plan a voyage in the standalone app: **bookmark** objects, build a **route**,
create a **mission**, and **preview the route** in the 2D/3D viewports. Plans are
saved in the local database and **persist across restarts**. No DCC required.

> UI: `unav_app/static`. Data model + API: see
> [`ROUTES_BOOKMARKS_MISSIONS.md`](ROUTES_BOOKMARKS_MISSIONS.md).

## Quick start

```bash
python scripts/run_demo.py      # then open the printed URL
```

1. **Find an object** — search (left), click a result to inspect it.
2. **Bookmark it** — *Bookmark selected object* (Selected object panel). It
   appears in the **Bookmarks** list; click a bookmark to re-select its object.
3. **Start a route** — type a name and click **New route** (Route panel).
4. **Add stops** — with an object selected, click **Add selected to route**. Each
   stop is appended as a waypoint (its position is cached for distances + 3D).
5. **Edit the route** — reorder waypoints with ↑/↓, remove with ×. The
   **distance summary** (legs + total parsecs) updates live.
6. **Preview** — the route draws as a **path** through its waypoints in both the
   3D points view and the 2D sky, with the waypoints highlighted. Click a
   waypoint to focus/select it.
7. **Create a mission** — give it a title and click **Create from active route**
   (Missions panel). It is saved with one timed segment per waypoint.

Everything you create is listed (Bookmarks / Saved routes / Missions), can be
deleted (×), and is still there after you stop and restart the server.

## What it is (MVP scope)

- **Bookmarks** — saved objects/coordinates (label, tags, notes).
- **Routes** — ordered, editable waypoint paths with a distance summary.
- **Missions** — a route + timed segments (a playable voyage; playback math lives
  in `unav_core.missions.playback`).
- **Preview** — a **path placeholder**: a polyline through the waypoints plus
  highlighted markers in 2D and 3D, with click-to-focus. It is a planning aid,
  not an animation (no auto-fly-through yet).

## Persistence

Bookmarks, routes and missions are stored as JSON rows in the same SQLite
database as the catalog (tables `bookmarks` / `routes` / `missions`). Saving is an
upsert that preserves creation order. Restarting the app (or pointing a new
server at the same `--db`) reloads them — verified by
`tests/test_api_voyage.py::test_voyage_persists_across_restart`.

## In the viewports

- **3D** — `UNAV3D.setRoute(waypoints)` draws a polyline through the waypoints'
  Cartesian positions plus constant-size markers; route stops are clickable
  (focus) even if they're not in the current visible-sector points.
- **2D sky** — the route is drawn through the waypoints' objects' RA/Dec (those
  currently loaded on the map), with markers; click a point to select.

The route overlay refreshes whenever the active route changes (add / reorder /
remove / select).

## Acceptance (and how it's met)

| Criterion | Met by |
| --- | --- |
| Build a simple astronomical route | New route → Add selected to route (waypoints with cached positions) |
| Route persists | `routes` table; reload on restart |
| Mission persists | `missions` table; reload on restart |
| Route appears visually | 3D polyline + markers and 2D path overlay |
| No DCC dependency | pure standalone engine + web UI |

## Out of scope (for now)

Automatic fly-through/playback in the viewport, drag-and-drop reorder, multi-route
missions beyond simple merge, and per-waypoint camera authoring in the UI. The
backend models already support timed segments and cameras
([`MISSIONS.md`](MISSIONS.md)); the UI exposes the MVP subset.
