# Cinema 4D Adapter — Workflow

The intended end-to-end artist workflow once the adapter exists. **Planning
only — nothing here is implemented yet.** It describes how a Cinema 4D user moves
between UNAV-SA and a C4D scene. Technical details live in
[`C4D_ADAPTER_PLAN.md`](C4D_ADAPTER_PLAN.md) and
[`C4D_API_CLIENT_PROTOCOL.md`](C4D_API_CLIENT_PROTOCOL.md).

## Prerequisites

- The **UNAV-SA local server** is running (outside Cinema 4D), populated with a
  dataset — e.g. the sample catalog, imported and enriched:
  ```bash
  python tools/run_unav_server.py --db data/unav.db --port 8765
  ```
  (See [`../../../docs/STANDALONE_APP_SHELL.md`](../../../docs/STANDALONE_APP_SHELL.md).)
- The C4D adapter installed in Cinema 4D (a Python plugin/script). It needs **no**
  extra Python packages — only the C4D SDK + stdlib.

## Sequence

```
 UNAV server                         C4D adapter (in Cinema 4D)              C4D scene
 ───────────                         ─────────────────────────              ─────────
     │   GET /health                         │
     │◀──────────────────────────────────────│  Connect (host/port)
     │   GET /navigator/state                 │
     │◀──────────────────────────────────────│  Build rig ─────────────────▶ Navigator null + Camera
     │   GET /visible-sector/current/render   │
     │◀──────────────────────────────────────│  Build points ──────────────▶ point clouds (per type)
     │   GET /missions                        │
     │◀──────────────────────────────────────│  Bake mission ──────────────▶ camera keyframes (timeline)
     │                                        │  (artist orbits the camera)
     │   POST /navigator/state                │
     │◀──────────────────────────────────────│  Send to UNAV  ◀─────────────  read C4D camera
     │   GET /visible-sector/current/render   │
     │◀──────────────────────────────────────│  Refresh points
```

## Steps

1. **Connect.** Open the UNAV panel in C4D; set host/port (default
   `127.0.0.1:8765`); click **Connect** → `GET /health`. The panel shows
   `ok · N objects` or an error (with a file-fallback option).

2. **Build the navigator rig.** **Pull state** → `GET /navigator/state`. The
   adapter creates a `UNAV Navigator` null containing a `Camera` (and a target
   null) positioned/aimed to mirror UNAV's navigator, mapping UNAV parsecs →
   C4D units (see the plan's coordinate mapping). FOV/clip map to the C4D camera.

3. **Build the visible sector.** **Pull points** →
   `GET /visible-sector/current/render` (or `POST /visible-sector/render` for a
   chosen pose). The adapter builds a **lightweight** point representation, one
   cloud per object type, coloured by the payload `display_color` and scaled by
   `display_size`. No per-object metadata is loaded here.

4. **Inspect an object.** Pick a point → the adapter reads its `uid` and calls
   `GET /objects/{uid}` to show the full record (name, type, source, coordinates,
   provenance) in the panel. Metadata is fetched for **one** object, on demand.

5. **Bake a mission.** **Pull missions** → `GET /missions`; choose one. The
   adapter maps the mission's segment cameras to **timeline keyframes** (using the
   segment durations and the document FPS) on the navigator camera, so the camera
   animates the voyage. (Linear key interpolation matches UNAV most closely.)

6. **Round-trip the camera.** The artist orbits/dollies the C4D camera. **Send to
   UNAV** reads the camera transform, inverse-maps it to a `NavigatorState`, and
   `POST /navigator/state`. Then **Refresh points** re-queries the visible sector
   from the new pose — so navigation done in C4D drives UNAV, and vice-versa.
   (**Focus object** uses `POST /navigator/focus/{uid}` instead, to frame a
   selected target.)

7. **Import route/waypoint labels.** **Pull routes** → `GET /routes`. The adapter
   creates named nulls (optionally text) at each waypoint's position, grouped
   under the route — handy for annotating a voyage in the scene.

## Offline / file fallback

If the server is unreachable (or for handoff to another machine):

1. In the UNAV standalone app, export the relevant JSON (render payload / mission
   / route / navigator state) to a file.
2. In C4D, choose **Import from file** in the adapter panel and pick the JSON.
3. The adapter applies the **same mapping** as the HTTP path. Round-tripping the
   camera back is unavailable offline (there is no server to receive it); the
   artist re-imports after the server is back.

## What this is (and is not)

- ✅ A **bridge**: it reflects UNAV's authoritative navigation/data into a C4D
  scene and pushes camera moves back.
- ❌ **Not** an astronomy tool inside C4D: it computes no coordinates, fetches no
  catalogs, runs no database, and owns no astronomy logic. All of that stays in
  UNAV-SA (see [`../../../docs/DCC_ADAPTER_STRATEGY.md`](../../../docs/DCC_ADAPTER_STRATEGY.md)).
