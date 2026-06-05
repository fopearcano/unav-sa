# UNAV-SA — API Endpoints

Reference for the local API (`unav_server`). All bodies/results are JSON. Models
are the canonical `unav_core` models (`CatalogObject`, `NavigatorState`, `Route`,
`Mission`, `ImportSummary`) plus a few server DTOs. See
[`LOCAL_API_SERVER.md`](LOCAL_API_SERVER.md).

| Method | Path | Body | Response |
| --- | --- | --- | --- |
| GET | `/health` | — | `{status, object_count}` |
| GET | `/datasets` | — | `[DatasetSummary]` |
| POST | `/datasets/import-jsonl` | `{path, dataset_name, enrich?}` | `ImportSummary` |
| GET | `/objects/search` | query: `q?`, `source?`, `object_type?`, `limit?` | `{count, objects: [CatalogObject]}` |
| GET | `/objects/{uid}` | — | `CatalogObject` (404 if missing) |
| GET | `/navigator/state` | — | `NavigatorState` |
| POST | `/navigator/state` | `NavigatorState` | `NavigatorState` |
| POST | `/navigator/focus/{uid}` | query: `distance?` | `NavigatorState` (404/400) |
| POST | `/navigator/move` | `{direction, distance?}` | `NavigatorState` (camera-relative step) |
| POST | `/visible-sector/query` | `{state?, sort?, object_types?, max_magnitude?}` | `VisibleSectorResponse` (`{count, capped, max_visible_objects, objects:[RenderPoint]}`) |
| POST | `/visible-sector/query-current` | — | `VisibleSectorResponse` (uses the current persisted state) |
| POST | `/visible-sector/render` | `{state?, sort?, object_types?, max_magnitude?}` | `RenderPayload` (`{count, points:[RenderPoint]}`) |
| GET | `/visible-sector/current/render` | — | `RenderPayload` |
| GET | `/routes` | — | `[Route]` |
| POST | `/routes` | `Route` | `Route` |
| GET | `/missions` | — | `[Mission]` |
| POST | `/missions` | `Mission` | `Mission` |

## Notes

- **Search** picks one primary filter (`q` → name; else `source`; else
  `object_type`; else lists objects), then applies any others in memory. `limit`
  is `1..1000` (default 50).
- **Focus** aims the navigator at object `{uid}`; with `distance` it also sits
  that far away along the view. `404` if the object is unknown, `400` if it has no
  Cartesian position.
- **Move** steps the navigator a camera-relative `direction`
  (`forward`/`back`/`left`/`right`/`up`/`down`) by `distance` pc (default 10);
  orientation and view params are preserved. Unknown direction or `distance <= 0`
  → `422`. See [`NAVIGATOR_STATE_LOOP.md`](NAVIGATOR_STATE_LOOP.md).
- **Query-current** computes the visible sector from the server's current
  persisted navigator state (the UI's manual refresh). See
  [`VISIBLE_SECTOR_REFRESH_MODEL.md`](VISIBLE_SECTOR_REFRESH_MODEL.md).
- **Visible-sector** uses the posted `state`, or the server's current navigator
  state if `state` is omitted. `sort` is `distance` (default) or `magnitude`;
  `object_types` is a list of type names; `max_magnitude` caps brightness.
  Unknown `sort` → `400`. `/visible-sector/query` returns **lightweight render
  objects** (no metadata/provenance) plus a `capped` flag; the `*/render`
  variants return the same objects as `points` for adapters. See
  [`RENDER_PAYLOAD.md`](RENDER_PAYLOAD.md). Full records load via
  `GET /objects/{uid}` on selection.
- **Invalid bodies** (e.g. an out-of-range `fov_degrees`) yield FastAPI's `422`.
- **`/datasets/import-jsonl`** reads a server-local path; missing file → `404`.

## Example

```bash
curl localhost:8765/health
curl "localhost:8765/objects/search?q=vega"
curl -X POST localhost:8765/visible-sector/query \
  -H 'content-type: application/json' \
  -d '{"state":{"position":{"x":0,"y":0,"z":0},"direction":{"x":0,"y":0,"z":-1},
       "up":{"x":0,"y":1,"z":0},"far_distance":100,"cone_angle_degrees":30}}'
```
