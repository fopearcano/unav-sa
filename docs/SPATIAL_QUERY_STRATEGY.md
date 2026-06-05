# UNAV-SA — Spatial Query Strategy

How UNAV-SA answers regional/spatial queries against the local cache
(`unav_core.db`) efficiently and correctly.

## Cone search (sky / RA–Dec)

`cone_search(db, ra_deg, dec_deg, radius_deg, *, limit=None)` finds objects
within an angular `radius_deg` of a sky position. It is a two-step
**prefilter + exact filter**:

### 1. Indexed bounding-box prefilter

A cheap SQL `WHERE` over the indexed `ra_deg`/`dec_deg` columns selects
candidates:

- **Declination:** `dec ∈ [dec0 − r, dec0 + r]` (clamped to `[−90, 90]`).
- **Right ascension:** half-width `Δα = asin(sin r / cos δ0)`.
  - If the cap reaches a pole (`cos δ0 ≤ sin r`, or `|δ0| + r ≥ 90`), the RA
    bound is dropped (all RA kept).
  - Otherwise `ra ∈ [ra0 − Δα, ra0 + Δα]`, with **wraparound** across the
    0°/360° boundary handled as `ra ≥ low OR ra ≤ high`.

The box is a *superset* of the cone, so the prefilter never drops a true match;
it only narrows the candidate set using indexes.

### 2. Exact angular filter

For each candidate, the exact great-circle separation is computed with a
**haversine** and compared to `radius_deg`. Results are returned sorted by
separation (nearest first), optionally limited.

### Why haversine (not Astropy) here

Keeping the `db` layer **Astropy-free** means importing `unav_core.db` stays
light and DCC-/runtime-friendly. The haversine gives the exact spherical angle;
`angular_separation_deg` is **cross-checked against Astropy** in the tests
(agreement ~1e-13°). Astropy remains the home of astronomy-grade coordinate
work in `unav_core.astro`.

### Correctness testing

`tests/test_spatial_queries.py` compares `cone_search` to a brute-force scan
over all objects (random, seeded) across centres including the poles and the
RA 0°/360° seam, asserting identical result sets — i.e. the bounding box never
causes a false negative.

## 3D proximity (Cartesian, parsecs)

`nearest_objects` and `objects_within_distance` operate on the Cartesian
`x/y/z` columns:

- **Squared Euclidean distance** `(x−X)² + (y−Y)² + (z−Z)²` is used for ordering
  and the radius test — no `sqrt`, so it is portable and fast.
- `objects_within_distance` adds a **bounding-box prefilter** (`x ∈ [X−r, X+r]`,
  etc.) on the indexed `x/y/z` columns before the exact squared-distance test.
- Objects without a full Cartesian position are excluded.

Populate `x/y/z` either from sources that provide them or via Phase 2
enrichment (`import ... --enrich`).

## Indexes used

`(ra_deg, dec_deg)` for cone prefilter; `x`, `y`, `z` for 3D prefilter;
`source`, `object_type`, `distance_pc`, `redshift`, `apparent_magnitude` for the
attribute queries.

## Limits & future work

- The bounding box widens near the poles; the exact filter keeps results
  correct, only doing slightly more candidate work there.
- For much larger working sets, an optional spatial index (HEALPix/HTM pixel
  column, or an R-tree / DuckDB / PostGIS backend) can be added **behind the
  same API** without changing callers. Not needed at Phase 3 scale.
