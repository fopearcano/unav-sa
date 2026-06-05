# UNAV-SA — Frontend Render Payload

The **lightweight** payload the 3D viewport (and any thin renderer/adapter) uses
to draw the visible sector. It deliberately omits metadata and provenance so a
viewport can render many points without loading per-object detail.

> Phase 12. Built by `unav_server.render`; full records are still available via
> `GET /objects/{uid}`.

## Endpoints

| Method | Path | Body | Response |
| --- | --- | --- | --- |
| POST | `/visible-sector/render` | `VisibleSectorRequest` (`state?`, `sort?`, `object_types?`, `max_magnitude?`) | `RenderPayload` |
| GET | `/visible-sector/current/render` | — | `RenderPayload` |

Both compute the visible sector (3D cone over the local cache) and return only
the renderable objects (those with Cartesian `x/y/z`). Unknown `sort` → `400`.

## `RenderPayload`

```json
{
  "count": 2,
  "points": [
    {
      "uid": "gaia:1",
      "source": "Gaia DR3",
      "object_type": "star",
      "x": 0.96, "y": -5.9, "z": 4.8,
      "color": "#cfe8ff",
      "size": 4.99,
      "name": "Vega"
    }
  ]
}
```

### `RenderPoint` fields

| Field | Meaning |
| --- | --- |
| `uid` | stable id (use it to fetch the full record / select) |
| `source` | originating catalog/service |
| `object_type` | canonical type name (`star`, `galaxy`, …) |
| `x`, `y`, `z` | Cartesian position (parsecs) |
| `color` | display colour (`#rrggbb`) — by object type |
| `size` | display size — by magnitude (brighter → larger; default if absent) |
| `name` | optional human-readable name |

**Not** included: `metadata`, `provenance`, photometry, redshift, parallax, etc.

## Why slim

- **Performance:** the viewport targets ≥ 10k points; shipping full
  `CatalogObject`s (with metadata + provenance) per point is wasteful. The slim
  payload keeps the response small and parsing cheap.
- **Separation:** `color`/`size` are *presentation*, computed server-side in
  `unav_server.render` (the same palette as the 2D legend) — not astronomy, so
  they stay out of `unav_core`.
- **On demand:** when the user selects a point, the UI fetches the full record
  with `GET /objects/{uid}`. Metadata is loaded for **one** object, not all.

## Palette & sizing

- Colour: a fixed `object_type → #rrggbb` map (`unav_server.render.TYPE_COLORS`),
  falling back to grey for unknown types.
- Size: `clamp(5 − magnitude/4, 1, 6)`; objects without a magnitude get a default.

Adapters that consume this payload map `x/y/z` (parsecs) into their host scene and
choose their own scale/handedness/up-axis — that mapping is the adapter's job (see
[`COORDINATE_CONVENTIONS.md`](COORDINATE_CONVENTIONS.md)).
