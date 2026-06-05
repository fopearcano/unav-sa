# UNAV-SA — Render Payload

The **lightweight** payload the navigator viewports (and any thin
renderer/adapter) use to draw the visible sector. It deliberately omits metadata
and provenance so a viewport can render many points without loading per-object
detail. Full records load **lazily**, one at a time, via `GET /objects/{uid}`
when a point is selected.

> Built by `unav_server.render.render_points`. See
> [`THREE_D_VIEW.md`](THREE_D_VIEW.md) for the viewport that consumes it and
> [`FRONTEND_RENDER_PAYLOAD.md`](FRONTEND_RENDER_PAYLOAD.md) for the original
> Phase-12 notes.

## The render object

Each renderable object (one with a Cartesian `x/y/z`) maps to a slim
`RenderPoint`:

| Field | Type | Meaning |
| --- | --- | --- |
| `uid` | str | stable id — fetch the full record / select with it |
| `name` | str? | optional human-readable name |
| `source` | str | originating catalog/service |
| `object_type` | str | canonical type name (`star`, `galaxy`, …) |
| `x`, `y`, `z` | float | ICRS Cartesian position (parsecs) |
| `ra_deg`, `dec_deg` | float? | sky position (degrees), when known |
| `distance_pc` | float? | distance (parsecs), when known |
| `display_color` | str | presentation colour (`#rrggbb`) — by object type |
| `display_size` | float | presentation size — by magnitude (brighter → larger) |

**Not** included: `metadata`, `provenance`, photometry, redshift, parallax, etc.
Those live in the full `CatalogObject` and load on demand.

## Endpoints

| Method | Path | Response | For |
| --- | --- | --- | --- |
| POST | `/visible-sector/query` | `VisibleSectorResponse` | the app's viewports |
| POST | `/visible-sector/render` | `RenderPayload` | adapters (chosen pose) |
| GET | `/visible-sector/current/render` | `RenderPayload` | adapters (current pose) |

All three compute the visible sector (3D cone over the local cache) and return
**only** renderable objects (those with `x/y/z`). Unknown `sort` → `400`.

### `POST /visible-sector/query` → `VisibleSectorResponse`

The app endpoint. Body is the usual `VisibleSectorRequest`
(`state?`, `sort?`, `object_types?`, `max_magnitude?`); `state` omitted uses the
server's current navigator state.

```json
{
  "count": 2,
  "capped": false,
  "max_visible_objects": 1000,
  "objects": [
    {
      "uid": "gaia:1", "name": "Vega", "source": "Gaia DR3", "object_type": "star",
      "x": 0.96, "y": -5.9, "z": 4.8,
      "ra_deg": 279.2, "dec_deg": 38.8, "distance_pc": 7.68,
      "display_color": "#cfe8ff", "display_size": 4.99
    }
  ]
}
```

- `count` — number of returned objects (`== len(objects)`).
- `capped` — **true** when the result was limited by the state's
  `max_visible_objects` (i.e. `count == max_visible_objects`); more objects may be
  visible than returned. The UI shows a warning. This is the standard "you hit the
  limit" signal — if exactly the cap is visible it may be a false positive, so the
  warning invites raising the cap rather than asserting truncation.
- `max_visible_objects` — the effective cap, echoed for the warning text.

### `/visible-sector/render` and `/current/render` → `RenderPayload`

The adapter endpoints. Same render objects under a `points` key, no cap flag:

```json
{ "count": 2, "points": [ { "uid": "gaia:1", ... } ] }
```

## Why slim

- **Performance.** The viewport targets ≥ 10k points; shipping full
  `CatalogObject`s (metadata + provenance) per point is wasteful. The slim payload
  keeps responses small and parsing cheap.
- **Separation.** `display_color` / `display_size` are *presentation*, computed
  server-side in `unav_server.render` (the same palette as the 2D legend) — not
  astronomy, so they stay out of `unav_core`.
- **Lazy detail.** On selection the UI fetches the full record with
  `GET /objects/{uid}`. Metadata is loaded for **one** object, not all.

## Palette & sizing

- Colour: a fixed `object_type → #rrggbb` map (`unav_server.render.TYPE_COLORS`),
  grey for unknown types.
- Size: `clamp(5 − magnitude/4, 1, 6)`; objects without a magnitude get a default
  (`2.5`).

Adapters consuming this payload map `x/y/z` (parsecs, right-handed) into their host
scene and choose their own scale/handedness/up-axis — that mapping is the adapter's
job (see [`COORDINATE_CONVENTIONS.md`](COORDINATE_CONVENTIONS.md)).
