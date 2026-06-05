# UNAV-SA — Visible Sector Model

How `unav_core.navigation.visible_sector.visible_objects(db, state, ...)` decides
what the navigator can currently see. All geometry is in the same Cartesian
**parsec** space as `CatalogObject.x/y/z` (see
[`COORDINATE_CONVENTIONS.md`](COORDINATE_CONVENTIONS.md)).

## Pipeline

```
NavigatorState + Database
        │
        ▼
1. DB candidates   objects_within_distance(db, cx, cy, cz, far_distance)   (indexed 3D box)
2. distance        near_distance ≤ |obj − camera| ≤ far_distance
3. cone            angle(obj − camera, direction) ≤ cone_angle_degrees
4. attributes      optional object_types / max_magnitude
5. sort            by distance (nearest first) or magnitude (brightest first)
6. cap             keep the first max_visible_objects
```

Only objects with a complete Cartesian position participate — 3D navigation
needs `x/y/z`. Objects without it (and objects beyond `far_distance`) are
dropped at step 1 by the indexed query.

## The maths (step 2–3)

For a candidate at position **p**, camera at **c**, view axis **d**:

- **distance:** `dist = |p − c|`; keep if `near ≤ dist ≤ far`.
- **cone:** let `offset = p − c`. The angle from the view axis is
  `acos( (offset · d̂) / |offset| )`; keep if `≤ cone_angle_degrees`. A point at
  the camera (`|offset| = 0`) is treated as inside.

`cone_angle_degrees` is the **half-angle** of the selection cone (measured from
the view axis to the cone edge) — independent of `fov_degrees`, which describes
the rendered field of view.

These predicates live in `unav_core.navigation.filters` and are pure (no DB), so
they are trivially unit-testable; `visible_sector` only orchestrates them over
the DB candidates.

## Sorting

- `sort="distance"` — ascending distance (nearest first).
- `sort="magnitude"` — ascending apparent magnitude (brightest first); objects
  with no magnitude sort last, ties broken by distance.

Any other value raises `ValueError`.

## Cap

The result is truncated to `state.max_visible_objects` after sorting, so the cap
keeps the *most relevant* objects for the chosen sort (nearest, or brightest).

## Why a box prefilter, then exact cone

The DB query uses the indexed `x/y/z` bounding box around the camera (fast,
selective), and the exact distance + cone tests run in Python over that bounded
candidate set — the same prefilter-then-refine pattern as the cone search in
[`SPATIAL_QUERY_STRATEGY.md`](SPATIAL_QUERY_STRATEGY.md). At Phase 3/7 working-set
sizes this is ample; larger sets can add a spatial index behind the same API.
