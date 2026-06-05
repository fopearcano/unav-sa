# UNAV-SA — 3D Navigator View

The interactive 3D point view in the standalone UI: the visible sector drawn as
GPU points in Cartesian `x/y/z` (parsecs), with an orbit/pan/zoom camera and
click-to-select. It is a **navigator aid**, not a render engine.

> Frontend: `unav_app/static/viewport3d.js` (Three.js) wired by
> `unav_app/static/app.js`. Backend: the lightweight render payload from
> `POST /visible-sector/query` (see [`RENDER_PAYLOAD.md`](RENDER_PAYLOAD.md)).
> Builds on the Phase-12 foundation in
> [`3D_NAVIGATOR_FOUNDATION.md`](3D_NAVIGATOR_FOUNDATION.md).

## Stack: Three.js, vendored, no build

Per [`STANDALONE_APP_STACK.md`](STANDALONE_APP_STACK.md), Three.js is **vendored
locally** (`unav_app/static/vendor/three.module.min.js`, r160, MIT) and loaded as
an ES module via an **import map** in `index.html`:

```html
<script type="importmap">{ "imports": { "three": "./vendor/three.module.min.js" } }</script>
<script type="module" src="viewport3d.js"></script>
```

No Node, no bundler, no runtime CDN. A modern browser (import-map + WebGL) is
required. If Three.js/WebGL fails to load, the 3D panel shows a fallback note and
the rest of the app (2D sky, search, inspect) keeps working.

## What you can do

| Action | How |
| --- | --- |
| **See the visible sector in 3D** | **Query visible sector** (or the 3D panel's **Render visible sector**) → `POST /visible-sector/query` → points appear. |
| **Orbit** | drag |
| **Pan** | right-drag, or shift-drag |
| **Zoom** | mouse wheel |
| **Select an object** | click a point → it gets a marker and the **Selected object** panel loads its full record (`GET /objects/{uid}`) |
| **Switch 2D ⇄ 3D** | the **3D points / 2D sky** toggle in the viewport header |
| **Reset the camera** | **Reset view** (reframes to the loaded points) |
| **Sync navigator ← view** | **Sync navigator to view** → `POST /navigator/state` (orbit, then re-query from the new pose) |
| **Focus an object** | **Focus navigator on object** → `POST /navigator/focus/{uid}` and centre the orbit |

### Colour & size

Each point's colour and size come **from the server** render payload
(`display_color` by object type, `display_size` by magnitude — brighter is
larger, with a default when magnitude is absent). The viewport just renders them;
the palette matches the 2D sky legend.

## 2D / 3D toggle

The viewport panel shows **one** view at a time, chosen by the header toggle:

- **3D points** — this view (Cartesian `x/y/z`).
- **2D sky** — the RA/Dec plate-carrée map (see
  [`2D_SKY_NAVIGATOR.md`](2D_SKY_NAVIGATOR.md)).

Both share the same selection: selecting in either view (or the results list)
highlights the object in the other and loads its record once. Switching views
resizes the now-visible canvas (the hidden one has zero size while collapsed).

## Object count & cap warning

After a visible-sector query the panel shows the **object count**
(`visible sector: N object(s)`). If the result hit the state's
`max_visible_objects`, a **warning** appears
(`⚠ result cap reached (max N); increase “max” to see more`). The cap signal is
`count == max_visible_objects` — the conventional "you may have hit the limit"
flag (see [`RENDER_PAYLOAD.md`](RENDER_PAYLOAD.md)). Raise **max** in the navigator
panel and re-query to see more.

## Performance

- Target **≥ 10k points**, not millions. The points are one `THREE.Points` object
  (a single `BufferGeometry` + `ShaderMaterial` draw call), so 10k renders
  comfortably. Click-picking and camera framing are `O(n)` per event — fine at
  10k.
- The payload is **lightweight** (no metadata/provenance per point), so a 10k
  response stays small and parses fast. Full records load per-object on selection.
- Keep the visible set bounded with the navigator's `far_distance`, `cone_angle`
  and `max_visible_objects`.

## Explicitly out of scope (no renderer-engine creep)

No lighting, materials, textures, meshes, shadows, post-processing or scene
authoring. The viewport draws coloured points, a selection marker and small axes —
nothing more. Richer rendering and host scenes are the job of **DCC adapters**,
which consume the same API/interchange (see
[`ADAPTER_COMMUNICATION_MODEL.md`](ADAPTER_COMMUNICATION_MODEL.md) and
[`DCC_ADAPTER_STRATEGY.md`](DCC_ADAPTER_STRATEGY.md)).

## Manual test checklist

Run the demo (`python scripts/run_demo.py`) and open the UI.

- [ ] **Points in 3D** — the 3D panel shows coloured points; the note shows a
      count. (Widen `far` / `cone` in the state panel and **Query visible sector**
      if empty.)
- [ ] **Orbit / pan / zoom** — drag orbits, right-drag (or shift-drag) pans, wheel
      zooms; the axes helper moves with the camera.
- [ ] **Select** — click a point → marker + the Selected object panel and results
      list update (full record fetched once).
- [ ] **Toggle** — switch to **2D sky** and back; both render and stay in sync.
- [ ] **Count / cap** — the count updates; set `max` low and re-query to see the
      cap warning.
- [ ] **2D still works** — the 2D sky pans/zooms/selects as before.
- [ ] **No DCC dependency** — everything runs in the browser against the local API.
