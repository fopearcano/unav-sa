# UNAV-SA — Time & Epochs

Time handling in `unav_core.astro.time`, backed by `astropy.time.Time`. Astropy
performs all calendar/JD conversions and time-scale handling so UNAV-SA never
hand-rolls them.

## Conventions

- **UTC is the default scale.** Naive `datetime` values and bare ISO strings are
  treated as UTC.
- **ISO-8601** is the string interchange format; output uses the `T`-separated
  form (Astropy's `isot`), e.g. `2000-01-01T12:00:00.000`.
- **Julian Date (JD)** is the numeric interchange format (days).
- **Epochs** (catalog reference epochs such as Gaia's `J2016.0`) are normalised
  to a canonical `"J<year>"` (Julian) or `"B<year>"` (Besselian) string.

## Functions

| Function | Description |
| --- | --- |
| `parse_time(value)` | Parse an ISO-8601 string, `datetime`, or `Time` into a UTC `astropy.time.Time` (an existing `Time` is returned unchanged). |
| `iso_to_julian_date(value)` | Julian Date (float) of an ISO string / datetime / `Time`. |
| `julian_date_to_iso(jd)` | ISO-8601 (`isot`) string for a Julian Date. |
| `current_time_utc()` | Current instant as a UTC `astropy.time.Time`. |
| `normalize_epoch(value)` | Canonical epoch string from a number, epoch string, or `Time`. |

## Examples

```python
from unav_core.astro.time import (
    iso_to_julian_date, julian_date_to_iso, current_time_utc, normalize_epoch,
)

iso_to_julian_date("2000-01-01T12:00:00")   # 2451545.0  (JD of J2000)
julian_date_to_iso(2451545.0)               # "2000-01-01T12:00:00.000"
current_time_utc().scale                     # "utc"

normalize_epoch(2016.0)     # "J2016.000"
normalize_epoch("J2000.0")  # "J2000.000"
normalize_epoch("2016")     # "J2016.000"   (bare number -> Julian)
normalize_epoch("B1950")    # "B1950.000"   (Besselian)
```

## Notes

- `parse_time` raises `TypeError` for unsupported types and `ValueError` for an
  empty string — it does not guess.
- Time **scales** beyond UTC (TT, TDB) are available through Astropy when epoch
  propagation and proper-motion application land in a later phase; the canonical
  schema currently stores positions at a catalog's reference epoch and records
  that epoch via [provenance](PROVENANCE_AND_VALIDATION.md).
- Requires Astropy; a missing install raises `AstropyNotInstalledError` (see
  [`ASTROPY_COORDINATE_LAYER.md`](ASTROPY_COORDINATE_LAYER.md)).
