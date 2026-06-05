# UNAV-SA — 3D Navigator Foundation

The first real 3D point-space view: the standalone shell renders the visible
sector as GPU points in Cartesian `x/y/z` (parsecs) with an orbit camera and
click-picking. It is a **navigator aid**, not a render engine.

> Phase 12 scope. Frontend: `unav_app/static/viewport3d.js` (Three.js). Backend:
> a lightweight render payload (see [`FRONTEND_RENDER_PAYLOAD.md`](FRONTEND_RENDER_PAYLOAD.md)).

## Stack: Three.js, vendored, no build

Per [`STANDALONE_APP_STACK.md`](STANDALONE_APP_STACK.md), Three.js is **vendored
locally** (`unav_app/static/vendor/three.module.min.js`, r160, MIT) and loaded as
an ES module via an **import map** in `index.html`:

```html
<script type="importmap">{ "imports": { "three": "./vendor/three.module.min.js" } }</script>
<script type="module" src="viewport3d.js"></script>
```

No Node, no bundler, no runtime CDN. A modern browser (import-map + WebGL) is
required. If Three.js/WebGL fails to load, the panel shows a fallback note and the
rest of the app keeps working.

## Features

- **Points** — one `THREE.Points` object (a single draw call) built from a
  `BufferGeometry` with per-point `position`, `pColor` and `size` attributes.
- **Colour by type / size by magnitude** — taken from the server render payload
  (the server owns the palette; the viewport just renders).
- **Camera controls** — orbit (drag to rotate, wheel to zoom), `Reset view`.
- **Selection / picking** — click a point; CPU projection finds the nearest point
  within a pixel threshold, marks it, and selects it (shared with the 2D map and
  the metadata panel). Selecting elsewhere highlights it in 3D too.
- **Axes helper** — small RGB axes for orientation.

## Navigation loop

The 3D camera and the navigator state are linked by explicit, **manual** actions
(per the phase's "query new visible sector manually"):

| Button | Effect |
| --- | --- |
| **Render visible sector** | `POST /visible-sector/render` with the current navigator state (from the state panel) → set points, frame the camera. |
| **Sync navigator to view** | read the 3D camera pose → `POST /navigator/state` (the frontend camera updates the navigator state). |
| **Reset view** | reframe the camera to the loaded points. |
| **Focus navigator on object** | `POST /navigator/focus/{uid}` and centre the 3D orbit on the object. |

So: drive the cone via the state panel → **Render**; or orbit in 3D → **Sync** →
**Render** to re-query from the new pose.

## Performance

- Target **≥ 10k points**; not millions. One Points object / draw call handles
  10k easily; picking is `O(n)` per click (fine at 10k).
- The render payload is **lightweight** — `uid/source/object_type/x/y/z/color/size`
  (+ optional `name`), with **no metadata or provenance**. Full records are
  fetched per-object only on selection (`GET /objects/{uid}`), so metadata is
  never loaded for every point.

## Explicitly out of scope (no renderer-engine creep)

No lighting, materials, textures, meshes, shadows, post-processing or scene
authoring. The viewport draws coloured points and a camera — nothing more. Richer
rendering (and host scenes) is the job of **DCC adapters**, which consume the same
API/interchange (see [`ADAPTER_COMMUNICATION_MODEL.md`](ADAPTER_COMMUNICATION_MODEL.md)).

## Manual viewport test checklist

Import the sample catalog (with `--enrich`, so objects have `x/y/z`) and start the
server (see [`STANDALONE_APP_SHELL.md`](STANDALONE_APP_SHELL.md)); open the UI.

- [ ] **See points in 3D** — the 3D panel shows coloured points; the note shows a
      point count. (Set a generous `far` / `cone` in the state panel, then
      **Render visible sector**, if empty.)
- [ ] **Orbit/zoom** — drag rotates, wheel zooms; the axes helper moves with it.
- [ ] **Select object** — click a point; it gets a wireframe marker, and the
      Selected object panel + results list update.
- [ ] **Focus object** — with an object selected, **Focus navigator on object**
      recenters the orbit and updates the navigator position.
- [ ] **Update navigator state** — orbit, click **Sync navigator to view**; the
      state panel position/direction update; **Render visible sector** re-queries.
- [ ] **No DCC dependency** — everything runs in the browser against the local API.
