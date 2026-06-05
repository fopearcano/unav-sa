# UNAV-SA — Astropy Coordinate & Time Layer

`unav_core.astro` is the astronomy-grade layer: coordinates, time and units,
built on **Astropy** so the maths is correct rather than hand-rolled. It is part
of the DCC-independent core and depends on nothing in `unav_app`, `unav_server`
or `adapters`.

> Phase 2 scope. See [`COORDINATE_CONVENTIONS.md`](COORDINATE_CONVENTIONS.md) and
> [`TIME_AND_EPOCHS.md`](TIME_AND_EPOCHS.md) for conventions.

## Dependency policy

- **Astropy is a core dependency** of the standalone engine (per
  [`UNAV_SA_ARCHITECTURE.md`](UNAV_SA_ARCHITECTURE.md)). It must **never** be
  required inside a DCC plugin runtime — adapters consume exported data instead.
- **Imports stay cheap.** Astropy is imported **lazily**: importing
  `unav_core.astro` or any submodule does no heavy work and no I/O. Astropy is
  pulled in only when a function that needs it runs.
- **No silent bad science.** If Astropy is missing, the lazy accessors in
  `unav_core.astro._backend` raise `AstropyNotInstalledError` with an actionable
  message. There is no hand-rolled fallback that could produce subtly wrong
  numbers. Use `astropy_available()` to feature-detect.

## Modules

| Module | Contents |
| --- | --- |
| `unav_core.astro._backend` | Lazy Astropy guard: `astropy_available`, `require_astropy`, `get_units`/`get_coordinates`/`get_time`, `AstropyNotInstalledError`. |
| `unav_core.astro.units` | `pc_to_ly`, `ly_to_pc`, `au_to_pc`, `pc_to_au`, `km_to_au`, `au_to_km`. |
| `unav_core.astro.time` | `parse_time`, `iso_to_julian_date`, `julian_date_to_iso`, `current_time_utc`, `normalize_epoch`. |
| `unav_core.astro.frames` | Frame registry: `SUPPORTED_FRAMES`, `DEFAULT_FRAME`, `normalize_frame_name`, `get_frame`. |
| `unav_core.astro.coordinates` | `skycoord_from_radec`, `radec_distance_to_cartesian`, `cartesian_to_radec_distance`, `icrs_to_galactic`, `galactic_to_icrs`, `angular_separation`. |
| `unav_core.astro.enrich` | `enrich_object_coordinates` — fills a `CatalogObject`'s `x/y/z`. |

Submodules are imported directly, e.g.
`from unav_core.astro.coordinates import radec_distance_to_cartesian`. The
package root stays deliberately import-light (no re-exports).

## Coordinate enrichment

`enrich_object_coordinates(obj, *, derive_distance_from_parallax=True)` is the
single bridge from `astro` to `unav_core.data`. It is **functional** — it returns
a new `CatalogObject` and never mutates the input.

- Already has `x/y/z` → returned unchanged (never overwritten).
- Has `ra_deg` + `dec_deg` and a distance → computes ICRS Cartesian `x/y/z` (pc).
- Distance source: `distance_pc` if present; otherwise, when enabled, a
  **positive** `parallax_mas` is inverted (`d[pc] = 1000 / parallax[mas]`) and
  stored. Non-positive parallaxes are never inverted.
- Nothing to compute → returned unchanged (Astropy is not even imported).

```python
from unav_core.data import CatalogObject, ObjectType
from unav_core.astro.enrich import enrich_object_coordinates

star = CatalogObject(uid="gaia-1", source="Gaia DR3", object_type=ObjectType.STAR,
                     ra_deg=45.0, dec_deg=30.0, parallax_mas=100.0)  # -> 10 pc
enriched = enrich_object_coordinates(star)
enriched.x, enriched.y, enriched.z   # ICRS Cartesian, parsecs
enriched.distance_pc                 # 10.0 (derived from parallax)
```

## Testing

`tests/test_astro_coordinates.py`, `tests/test_astro_time.py` and
`tests/test_astro_units.py` cover known values (e.g. JD of J2000, the galactic
pole, IAU unit factors), round-trips, enrichment, and the
`AstropyNotInstalledError` fallback (verified by temporarily hiding Astropy).
