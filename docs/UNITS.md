# UNAV-SA — Units

The unit conventions UNAV-SA stores data in, and the Astropy-backed helpers for
converting between common astronomical length units. Conversions use **IAU-defined
factors via `astropy.units`**, never hand-coded constants.

> Part of the Phase-2 astronomy layer (`unav_core.astro`). See
> [`ASTROPY_COORDINATE_LAYER.md`](ASTROPY_COORDINATE_LAYER.md) and
> [`COORDINATE_CONVENTIONS.md`](COORDINATE_CONVENTIONS.md).

## Canonical units

UNAV-SA stores everything in one fixed set of units, so every layer (core, app,
server, adapters) speaks the same language. The full map is
`unav_core.data.schema.CANONICAL_UNITS`:

| Quantity | Canonical unit |
| --- | --- |
| Sky angles (`ra_deg`, `dec_deg`) | degrees |
| **Distance** (`distance_pc`) | **parsec (pc)** |
| **Cartesian position** (`x`, `y`, `z`) | **parsec (pc)** |
| Parallax (`parallax_mas`) | milliarcseconds (mas) |
| Redshift (`redshift`) | dimensionless |
| Radial velocity (`radial_velocity_kms`) | km/s |
| Proper motion (`*_masyr`) | mas/yr |
| Magnitudes / colour | mag |

**Parsec is the canonical distance**, and **Cartesian `x/y/z` are parsecs** — the
same length unit for stars (pc–kpc) and, honestly, for Solar-System bodies whose
AU-scale positions become tiny in parsecs (see
[`EPOCH_OBJECTS.md`](EPOCH_OBJECTS.md)). Connectors must convert source units to
this convention before normalising.

## Conversion helpers (`unav_core.astro.units`)

Plain `float` in, plain `float` out (the schema stores plain numbers); the
conversion itself is performed by Astropy.

| Function | Converts |
| --- | --- |
| `pc_to_ly(value)` | parsecs → light-years |
| `ly_to_pc(value)` | light-years → parsecs |
| `au_to_pc(value)` | astronomical units → parsecs |
| `pc_to_au(value)` | parsecs → astronomical units |
| `km_to_au(value)` | kilometres → astronomical units |
| `au_to_km(value)` | astronomical units → kilometres |

```python
from unav_core.astro.units import pc_to_ly, au_to_pc

pc_to_ly(1.0)    # ≈ 3.2616 light-years
au_to_pc(1.0)    # ≈ 4.84814e-6 parsecs
```

Reference factors (from the IAU definitions Astropy uses):

- `1 pc ≈ 3.261564 ly ≈ 206264.806 au`
- `1 au = 149,597,870.7 km`

## Requires Astropy

These helpers call `astropy.units` and therefore need Astropy installed. If it is
missing, the lazy accessor raises `AstropyNotInstalledError` with an actionable
message — there is **no** hand-rolled fallback that could produce subtly wrong
numbers (see [`ASTROPY_COORDINATE_LAYER.md`](ASTROPY_COORDINATE_LAYER.md)).

## What this phase does / does not do

- ✅ Length-unit conversions (pc/ly/au/km) and the canonical-unit map.
- ❌ Per-field automatic unit coercion of incoming connector data — that is the
  connector's job (Phase 5+), which converts to `CANONICAL_UNITS` on normalise.
- ❌ Flux/photometric system conversions (magnitudes are stored as provided).

## Testing

`tests/test_astro_units.py` checks the round-trips and the IAU factors (e.g.
`1 au = 149,597,870.7 km`, `pc↔ly`, `pc↔au`).
