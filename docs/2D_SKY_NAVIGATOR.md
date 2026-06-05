# UNAV-SA — 2D Sky Navigator

A functional 2D sky map in the standalone shell: it plots RA/Dec points from a
sky-region query, search, or the visible sector, and supports pan/zoom,
click-to-select, hover labels, colour by object type and size by magnitude.

> Phase 11 scope. Frontend: `unav_app/static/sky.js` (the `SkyMap`). Backend:
> two endpoints below. Built on the shell from
> [`STANDALONE_APP_SHELL.md`](STANDALONE_APP_SHELL.md).

## Projection & limitations (read this)

The map uses a **simple plate carrée / equirectangular** projection:

```
screen_x ∝ (RA − RA_center)   (wrapped to ±180°)
screen_y ∝ (Dec − Dec_center)
```

- There is **no `cos(dec)` correction**, so east–west scale is **not** preserved;
  distortion grows toward the poles. This is **not** an accurate sky projection
  (no gnomonic/orthographic/Aitoff, no WCS) — do not treat angular separations or
  shapes on the map as accurate, especially at high `|Dec|`.
- RA wrap at the 0°/360° seam is handled for panning and region queries, but the
  flat map still splits objects across the seam visually when zoomed in near it.
- Proper projections (and accurate angular measures) belong to a later phase and
  would use the astronomy layer (`unav_core.astro`); the 2D map here is a
  navigator aid, not a science-grade chart.

## Interaction

- **Pan:** drag.
- **Zoom:** mouse wheel (zooms toward the cursor). Scale is clamped.
- **Select:** click a point (within a few pixels) → fetches and shows the
  object's metadata, highlights it on the map and in the results list.
- **Hover:** shows the object's name/type label.
- **Colour by type** (legend below the map); **size by magnitude** where
  available (brighter = larger; objects without a magnitude use a default dot).

Toolbar: **Full sky** (load everything with RA/Dec), **Load region in view**
(query just the current viewport), **Fit** (frame the loaded objects).

Objects with only Cartesian `x/y/z` (no RA/Dec) are listed but not plotted (the
"N/M on sky" note reflects this).

## Backend endpoints

| Method | Path | Body | Response |
| --- | --- | --- | --- |
| POST | `/sky/query-region` | `{ra_min, ra_max, dec_min, dec_max, limit?}` | `{count, objects}` |
| GET | `/visible-sector/current` | — | `{count, objects}` (current navigator state) |

`/sky/query-region` returns objects within an RA/Dec box (degrees). `ra_min >
ra_max` selects a box that **wraps** across the 0/360 seam. `dec_max ≥ dec_min`
is required (else `422`). Only objects with both `ra_deg` and `dec_deg` are
returned. Backed by `unav_core.db.objects_in_sky_box` (uses the indexed RA/Dec
columns).

```bash
curl -X POST localhost:8765/sky/query-region -H 'content-type: application/json' \
  -d '{"ra_min":0,"ra_max":360,"dec_min":-90,"dec_max":90}'
```

## No DCC dependency

The 2D view is plain HTML/canvas/JS served by the local API. It contains **no
DCC code and no backend logic** — it only renders RA/Dec the API provides.

## Manual test checklist

Setup (see [`STANDALONE_APP_SHELL.md`](STANDALONE_APP_SHELL.md) to import the
sample catalog), then open <http://127.0.0.1:8765/>.

- [ ] **Sample catalog appears in 2D** — on load (or after **Full sky**) the
      canvas shows scattered points; the note reads `N/M on sky`.
- [ ] **Pan/zoom** — dragging moves the field; the wheel zooms toward the cursor;
      RA/Dec gridlines and labels update.
- [ ] **Select object** — click a point; it gets a white ring and the matching
      results-list row highlights.
- [ ] **Selected metadata appears** — the Selected object panel fills with
      uid/name/type/source and coordinates.
- [ ] **Hover label** — hovering a point shows its name/type.
- [ ] **Colour & size** — points are coloured by type (legend) and brighter
      objects are larger.
- [ ] **Load region in view** — zoom into a patch, click **Load region in view**;
      only objects in that RA/Dec window load (count in the status bar).
- [ ] **Focus navigator on selected** — with an object that has `x/y/z` selected,
      click **Focus navigator on object**; the navigator position updates.
- [ ] **No DCC dependency** — everything runs in the browser against the local
      API; no Cinema 4D/Blender/etc. involved.
