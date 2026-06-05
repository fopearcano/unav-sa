# UNAV-SA — Coordinate Conventions

The conventions every layer assumes. Implemented in `unav_core.astro` on top of
Astropy; the canonical schema (`unav_core.data`) stores positions accordingly.

## Frames

- **Default frame: ICRS.** `ra_deg`/`dec_deg` in `CatalogObject` are ICRS
  degrees. `Dataset.coordinate_system` defaults to `"ICRS"`.
- The frame registry (`unav_core.astro.frames`) maps short names to Astropy
  frame classes. `SUPPORTED_FRAMES = ("icrs", "galactic", "fk5", "fk4")`;
  `DEFAULT_FRAME = "icrs"`. Use `get_frame(name)` for the class and
  `normalize_frame_name(name)` to canonicalise (case-insensitive).

## Angles

- **Right ascension** `ra_deg ∈ [0, 360)` degrees.
- **Declination** `dec_deg ∈ [-90, 90]` degrees.
- These ranges are enforced structurally by `CatalogObject`.
- **Galactic** longitude/latitude `(l, b)` are returned in degrees by
  `icrs_to_galactic`; `galactic_to_icrs` is the inverse.
- **Angular separation** is returned in degrees (`angular_separation`).

## Distance

- **Parsecs (pc)** everywhere: `distance_pc`, and the Cartesian `x/y/z`.
- **Distance from parallax:** `d[pc] = 1000 / parallax[mas]`, valid only for a
  **positive** parallax. Non-positive parallaxes (real, noisy Gaia measurements)
  do not yield a distance — see
  [`PROVENANCE_AND_VALIDATION.md`](PROVENANCE_AND_VALIDATION.md).

## Cartesian convention

`radec_distance_to_cartesian` / `cartesian_to_radec_distance` use the ICRS
rectangular system Astropy produces, in parsecs:

```
x → (RA = 0°,  Dec = 0°)
y → (RA = 90°, Dec = 0°)
z → (Dec = +90°, north celestial pole)
```

Equivalently:

```
x = d · cos(dec) · cos(ra)
y = d · cos(dec) · sin(ra)
z = d · sin(dec)
```

Quick checks (distance = 1 pc): `(ra=0,  dec=0)  → (1, 0, 0)`,
`(ra=90, dec=0) → (0, 1, 0)`, `(dec=90) → (0, 0, 1)`.

These are right-handed, equatorial axes — **not** a DCC/scene coordinate system.
Mapping to a host's axes (handedness, up-axis, scale) is an **adapter**
responsibility, not the core's.

## Unit conversions

`unav_core.astro.units` provides IAU-defined conversions backed by Astropy:
`pc_to_ly`, `ly_to_pc`, `au_to_pc`, `pc_to_au`, `km_to_au`, `au_to_km`
(`1 au = 149,597,870.7 km`, `1 pc ≈ 3.261564 ly ≈ 206264.806 au`).
