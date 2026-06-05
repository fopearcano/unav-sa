# UNAV-SA — Astropy Usage

Where and how UNAV-SA uses **Astropy**, and the rules that keep that usage
correct, cheap to import, and safely contained. Astropy is the authoritative
engine for all astronomy maths in the standalone core; nothing else hand-rolls
coordinate or time conversions.

> Companion docs: [`COORDINATE_PIPELINE.md`](COORDINATE_PIPELINE.md) (the data
> flow), [`ASTROPY_COORDINATE_LAYER.md`](ASTROPY_COORDINATE_LAYER.md) (the API),
> [`COORDINATE_CONVENTIONS.md`](COORDINATE_CONVENTIONS.md) and
> [`TIME_AND_EPOCHS.md`](TIME_AND_EPOCHS.md) (the conventions).

## Why Astropy

Coordinate frames, RA/Dec ↔ Cartesian, parallax/distance, ICRS ↔ Galactic, time
scales and epoch propagation, and IAU-defined unit factors are subtle and easy to
get *almost* right. UNAV-SA delegates all of it to Astropy so the numbers are
correct rather than plausible. There is **no** hand-rolled fallback that could
produce subtly wrong science.

## The three rules

1. **Astropy is a core dependency — of the engine, not of every import.**
   It is declared in `pyproject.toml` and required to run the standalone engine,
   app and server. But `import unav_core` (and `import unav_core.astro`, and the
   data layer) must stay cheap: importing them performs **no** Astropy import and
   no I/O.

2. **Astropy is imported lazily, behind one guard.**
   `unav_core.astro._backend` is the single choke point. Submodules and the data
   layer pull Astropy in **inside the function that needs it**, never at module
   top level:

   ```python
   from unav_core.astro._backend import get_coordinates, get_units
   def radec_distance_to_cartesian(ra, dec, distance_pc):
       coord, u = get_coordinates(), get_units()   # imported on first use
       ...
   ```

   The sample generator and the DB importer follow the same pattern: their module
   imports are Astropy-free, and they `from unav_core.astro.enrich import …`
   *inside* the call that enriches.

3. **Astropy must never run inside a DCC runtime.**
   Cinema 4D (and future Blender/Houdini/Unreal) adapters are **thin clients**:
   they consume already-computed data over HTTP/JSON and do **no** astronomy. The
   whole `unav_core.astro` layer — and Astropy with it — stays on the standalone
   side of that boundary. See [`DCC_ADAPTER_STRATEGY.md`](DCC_ADAPTER_STRATEGY.md)
   and [`PRODUCT_IDENTITY.md`](PRODUCT_IDENTITY.md).

## Where Astropy is used

All of it lives under `unav_core.astro`:

| Module | Astropy used for |
| --- | --- |
| `_backend` | the lazy import guard (`astropy_available`, `require_astropy`, `get_units`/`get_coordinates`/`get_time`, `AstropyNotInstalledError`). |
| `coordinates` | `SkyCoord` / `CartesianRepresentation`: RA/Dec(/distance) ↔ Cartesian, ICRS ↔ Galactic, angular separation. |
| `frames` | mapping short frame names to `astropy.coordinates` frame classes. |
| `time` | `astropy.time.Time`: ISO ↔ Julian Date, time scales, epoch normalisation. |
| `units` | `astropy.units`: IAU-defined pc/ly/au/km conversions. |
| `enrich` | the bridge: uses `coordinates` to fill a `CatalogObject`'s `x/y/z`. |

Callers **outside** `astro` never `import astropy` themselves. They go through
the functions above (most often `enrich_object_coordinates`). The two callers
that produce Cartesian positions are:

- `unav_core.data.sample_generator` — enriches generated objects (default on);
- `unav_core.db.importer` — enriches on import when `enrich=True`.

Layers that only *consume* already-Cartesian data — `unav_core.db.queries`
(SQL box + squared distance), `unav_core.navigation` (`Vec3` geometry),
`unav_server.render` (presentation) — deliberately use **plain Python maths** on
the stored parsecs and carry **no** Astropy dependency. That is intentional: it
keeps the navigation/serving hot path light.

## Feature-detecting Astropy

```python
from unav_core.astro._backend import astropy_available, AstropyNotInstalledError

if astropy_available():
    from unav_core.astro.enrich import enrich_object_coordinates
    obj = enrich_object_coordinates(obj)
```

If a coordinate/time function is called without Astropy installed, it raises
`AstropyNotInstalledError` (an `ImportError` subclass) with an install hint —
rather than guessing. Enrichment with nothing to compute (no distance) does not
import Astropy at all.

## Determinism

Coordinate enrichment is a pure function of its float inputs, so the sample
catalog is reproducible: `generate_sample_catalog(100, seed=42)` yields the same
`x/y/z` every run, and the committed `samples/sample_catalog.jsonl` is
byte-stable. Generation attaches **no** wall-clock timestamp
(`provenance.retrieved_at is None`); it records only the frame, epoch and units.

## Versioning

Astropy's version is pinned by `pyproject.toml`'s lower bound. Cartesian values
can differ at the ULP level across Astropy releases; tests assert conversions
with tolerances and recompute expected values **in-process** (never byte-compare
the committed catalog's `x/y/z` against a fresh Astropy version).

## Tests

`tests/test_astro_coordinates.py`, `tests/test_astro_time.py`,
`tests/test_astro_units.py` cover known values, round-trips and enrichment, and
verify the `AstropyNotInstalledError` path by temporarily hiding Astropy.
`tests/test_imports.py` guards that `import unav_core` / `unav_app` /
`unav_server` stay Astropy-free.
