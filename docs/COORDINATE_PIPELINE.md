# UNAV-SA — Coordinate Pipeline

How an astronomical position travels through UNAV-SA, and **where every
coordinate calculation happens**. The guiding rule:

> All astronomical coordinate conversion goes through `unav_core.astro`
> (Astropy-backed). No other layer hand-rolls spherical trig or RA/Dec ↔
> Cartesian maths.

This keeps the science in one audited place and keeps every other layer — the
sample generator, the importer, the database, the server, the adapters — free of
duplicated, drift-prone astronomy. See
[`COORDINATE_CONVENTIONS.md`](COORDINATE_CONVENTIONS.md) for the frames/units and
[`ASTROPY_USAGE_IN_UNAV.md`](ASTROPY_USAGE_IN_UNAV.md) for the Astropy policy.

## The single conversion point

`unav_core.astro.coordinates` is the **only** module that converts between sky
coordinates and Cartesian space. Everything else calls it (directly, or via the
`enrich` bridge):

| Function | Converts |
| --- | --- |
| `skycoord_from_radec(ra, dec, distance_pc=None)` | RA/Dec(/distance) → `SkyCoord` |
| `radec_distance_to_cartesian(ra, dec, distance_pc)` | RA/Dec/distance → ICRS `(x, y, z)` pc |
| `cartesian_to_radec_distance(x, y, z)` | ICRS `(x, y, z)` pc → RA/Dec/distance |
| `icrs_to_galactic(ra, dec)` / `galactic_to_icrs(l, b)` | ICRS ↔ Galactic |
| `angular_separation(ra1, dec1, ra2, dec2)` | on-sky angle (deg) |

The bridge into the data layer is `unav_core.astro.enrich`:

`enrich_object_coordinates(obj)` takes a `CatalogObject` and returns a **new** one
with `x/y/z` filled from `ra_deg`/`dec_deg` + a distance (`distance_pc`, or a
**positive** `parallax_mas` inverted to `1000/parallax`). It never mutates the
input, never overwrites existing `x/y/z`, and only imports Astropy when there is
something to compute.

## End-to-end flow

```
 generate ──▶ enrich (astro) ──▶ JSONL ──▶ import (+enrich) ──▶ SQLite ──▶ query ──▶ render / inspect
   RA/Dec        x/y/z [pc]                  x/y/z [pc]          x/y/z      Cartesian    pass-through
 (sample gen)  radec→cartesian             (idempotent)        columns    + angular     (no maths)
```

1. **Generate** — `unav_core.data.sample_generator` draws valid `ra_deg ∈ [0,360)`
   / `dec_deg ∈ [-90,90]` and a distance (or redshift). By default it then calls
   `enrich_object_coordinates` to fill ICRS Cartesian `x/y/z` (parsecs) for every
   object with a usable distance. The coordinate system (`reference_frame="ICRS"`,
   `epoch="J2000.0"`) and the unit convention (`CANONICAL_UNITS`) are recorded in
   each object's `provenance`. Redshift-only objects (galaxies, quasars) stay
   sky-only. `--no-enrich` skips this step.
2. **Import** — `unav_core.db.importer.import_jsonl_to_db(..., enrich=True)` runs
   the same `enrich_object_coordinates` over every object before insert, so any
   catalog (sample or real connector output) gains `x/y/z` if it has the inputs.
   Enrichment is **idempotent**: objects that already carry `x/y/z` (e.g. the
   enriched sample) pass through unchanged.
3. **Store** — the `objects` table persists `x/y/z` (and `ra_deg`/`dec_deg`,
   `distance_pc`, …) with indexes on each Cartesian axis for fast prefiltering.
   No conversion happens here — values are stored as computed.
4. **Query** — the visible sector (below) filters spatially in **Cartesian**
   space and angularly within the view cone. The 2D sky uses RA/Dec directly
   (plate-carrée; see [`2D_SKY_NAVIGATOR.md`](2D_SKY_NAVIGATOR.md)).
5. **Render / inspect** — `unav_server.render.render_points` and
   `GET /objects/{uid}` **pass coordinates straight through**; presentation
   (colour/size) is not astronomy and does no coordinate maths.

## Visible-sector query (spatial + angular)

`unav_core.navigation.visible_sector.visible_objects(db, state)`:

1. **Cartesian prefilter** — `objects_within_distance` selects rows within
   `far_distance` of the camera using an indexed `x/y/z` bounding box, then an
   exact squared-distance test. Only rows with a full Cartesian position are
   considered (`x`, `y`, `z` all non-null).
2. **Distance filter** — keep objects in `[near_distance, far_distance]`.
3. **Angular (cone) filter** — `filters.within_cone` keeps objects whose offset
   from the camera lies within `cone_angle_degrees` of the view direction (the
   angle between the offset vector and the view axis).
4. **Attribute filters** — optional type / magnitude caps.
5. **Sort + cap** — by distance or magnitude, capped to `max_visible_objects`.

The state inputs are validated to be *sufficient* by construction:
`NavigatorState` requires a non-zero `direction`/`up` and `far_distance >
near_distance`, and `Vec3` requires finite components.

## When coordinates are insufficient

The pipeline **fails clearly** rather than inventing positions:

- **No distance** → no Cartesian. `enrich_object_coordinates` leaves `x/y/z`
  unset (a redshift is *not* turned into a Euclidean distance here — that needs a
  cosmology and is out of scope). Such objects are honestly sky-only.
- **3D navigation requires Cartesian.** Objects without `x/y/z` are **excluded**
  from the visible sector and the 3D render payload — never silently placed at
  the origin or projected with a bogus distance. They remain fully usable in the
  2D sky view (which needs only RA/Dec) and in search/inspect.
- **Non-positive parallax** (real, noisy Gaia values) is never inverted to a
  distance — see [`PROVENANCE_AND_VALIDATION.md`](PROVENANCE_AND_VALIDATION.md).
- **Astropy missing** → the lazy accessors raise `AstropyNotInstalledError` with
  an actionable message instead of falling back to hand-rolled (and likely wrong)
  maths. See [`ASTROPY_USAGE_IN_UNAV.md`](ASTROPY_USAGE_IN_UNAV.md).

## Where coordinates are touched (audit)

| Touchpoint | Module | Coordinate work | Routes through `astro`? |
| --- | --- | --- | --- |
| Sample generation | `unav_core.data.sample_generator` | RA/Dec/distance → `x/y/z` | ✅ via `enrich` |
| DB import (`--enrich`) | `unav_core.db.importer` | RA/Dec/distance → `x/y/z` | ✅ via `enrich` |
| Enrichment bridge | `unav_core.astro.enrich` | parallax→distance, RA/Dec/dist → `x/y/z` | ✅ (is `astro`) |
| Conversions | `unav_core.astro.coordinates` | all RA/Dec ↔ Cartesian, ICRS ↔ Galactic | ✅ (is `astro`) |
| Spatial query | `unav_core.db.queries` | Cartesian box + squared distance (SQL) | n/a (pure geometry on stored `x/y/z`) |
| Visible sector | `unav_core.navigation.{visible_sector,filters}` | distance + cone (pure `Vec3` geometry) | n/a (pure geometry) |
| 2D sky box | `unav_core.db.queries.objects_in_sky_box` | RA/Dec range (plate-carrée) | n/a (angular ranges) |
| Render payload | `unav_server.render` | none — passes `x/y/z` through | n/a |
| Object inspect | `GET /objects/{uid}` | none — returns stored fields | n/a |

The rows marked *pure geometry* operate on **already-converted** Cartesian
parsecs (vector subtraction, dot products, Euclidean distance) — they perform no
astronomical coordinate conversion, so they correctly stay out of `astro` and
free of an Astropy dependency (keeping the navigation layer light).

## Tests

- `tests/test_astro_coordinates.py` — known directions, RA/Dec↔Cartesian
  round-trip, ICRS↔Galactic (galactic pole), angular separation, enrichment
  (incl. distance-from-parallax and the missing-distance fallback).
- `tests/test_sample_generator.py` — the generator fills `x/y/z` through Astropy,
  records frame/epoch/units in provenance, and the `--no-enrich` opt-out.
- `tests/test_db_importer.py::test_enrich_on_import` — DB enrichment.
- `tests/test_coordinate_pipeline.py` — the centralised pipeline end-to-end
  (generate → import → spatial query) yields spatially meaningful results.
