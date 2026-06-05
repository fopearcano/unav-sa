# UNAV-SA — Core Data Schema

The canonical, **DCC-independent** object model that every record is normalised
to. Defined in `unav_core.data` and `unav_core.provenance` using Pydantic v2.

> Phase 1 scope: pure data models, validation and JSONL interchange. **No**
> Astropy and **no** connectors yet (see [`ROADMAP.md`](ROADMAP.md)).

## Modules

| Module | Contents |
| --- | --- |
| `unav_core.data.object_types` | `ObjectType` enum |
| `unav_core.data.schema` | `CatalogObject`, `CANONICAL_UNITS` |
| `unav_core.data.dataset` | `Dataset` |
| `unav_core.data.io` | `write_jsonl`, `read_jsonl`, `validate_jsonl` |
| `unav_core.provenance.provenance` | `Provenance` |
| `unav_core.provenance.validation` | validation helpers (see [PROVENANCE_AND_VALIDATION](PROVENANCE_AND_VALIDATION.md)) |

Convenience re-exports are available from the package roots, e.g.
`from unav_core.data import CatalogObject, Dataset, ObjectType`.

## `ObjectType`

A small, source-independent taxonomy (a `str` enum, so it serialises to its
lowercase value):

`star`, `galaxy`, `quasar`, `planet`, `moon`, `asteroid`, `comet`,
`spacecraft`, `nebula`, `custom`, `unknown`.

Connectors map native source types with `ObjectType.coerce(value)`, which is
case-insensitive and returns `UNKNOWN` for unrecognised values or `None`.

## `CatalogObject`

The canonical record. Required: `uid`, `source`, `object_type`. Everything else
is optional. Source-specific extras go in `metadata`; origin info in
`provenance`.

| Field | Type | Unit | Notes |
| --- | --- | --- | --- |
| `uid` | str | — | **Globally unique** UNAV id (non-empty); normally source-prefixed — see [Identity](#identity-uid--native_id). |
| `source` | str | — | Originating catalog/service (non-empty). |
| `object_type` | `ObjectType` | — | Canonical type. |
| `name` | str? | — | Human-readable designation. |
| `native_id` | str? | — | Source-native catalog id (the un-prefixed id), if any. |
| `ra_deg` | float? | deg | Right ascension, `[0, 360)`. |
| `dec_deg` | float? | deg | Declination, `[-90, 90]`. |
| `distance_pc` | float? | pc | Distance, `>= 0`. |
| `parallax_mas` | float? | mas | **May be `<= 0`** (real noisy measurements). |
| `redshift` | float? | — | Redshift `z`. |
| `radial_velocity_kms` | float? | km/s | |
| `proper_motion_ra_masyr` | float? | mas/yr | |
| `proper_motion_dec_masyr` | float? | mas/yr | |
| `apparent_magnitude` | float? | mag | |
| `absolute_magnitude` | float? | mag | |
| `color_index` | float? | mag | |
| `spectral_type` | str? | — | e.g. `"G2V"`. |
| `x`, `y`, `z` | float? | pc | Cartesian position. |
| `metadata` | dict | — | Source-specific extras (default `{}`). |
| `provenance` | `Provenance`? | — | Origin/audit record. |

### Identity (`uid` / `native_id`)

`uid` is the **globally unique UNAV object id** — unique across *all* sources and
datasets, not just within one catalog. It is the stable handle everything else
references: routes/missions/bookmarks store a `uid`, the database keys on it,
duplicate detection is global, and merging two datasets must not collide.

To keep ids globally unique and self-describing, a `uid` is **normally
source-prefixed** (`<source>:<native-id>`):

| Source | Example `uid` |
| --- | --- |
| Gaia | `gaia:5853498713160606720` |
| SDSS | `sdss:1237654607730835537` |
| DESI | `desi:targetid-39627640566321887` |
| JPL Horizons (epoch object) | `jpl:mars:2026-01-01T00:00:00` |
| Custom / user object | `custom:station-alpha` |

The **un-prefixed**, source-native id goes in `native_id` (and/or `metadata`),
*not* in `uid`:

```python
CatalogObject(
    uid="gaia:5853498713160606720",   # globally unique UNAV id
    native_id="5853498713160606720",  # source-native catalog id
    source="Gaia DR3",
    object_type=ObjectType.STAR,
)
```

Rules of thumb:

- **A `uid` must be globally unique and stable.** The same physical object fetched
  twice must get the same `uid`; two different objects must never share one.
- **Source-specific ids belong in `native_id` or `metadata`**, never in `uid`
  alone (a bare native id like `123456789` is not globally unique — Gaia and SDSS
  could both use it).
- The prefix convention is a *strong recommendation*, not a structural constraint:
  the model only enforces non-empty. Connectors are responsible for minting
  prefixed, globally unique ids.

### Structural validation (enforced by the model)

- `uid` and `source` must be non-empty.
- `ra_deg ∈ [0, 360)`, `dec_deg ∈ [-90, 90]`, `distance_pc >= 0`.
- All numeric fields must be **finite** — `NaN`/`inf` are rejected.
- Unknown top-level fields are rejected (`extra="forbid"`): anything
  source-specific belongs in `metadata`.

Note `parallax_mas` and `redshift` are deliberately **not** range-bounded here;
their quality is assessed by the validation helpers (a negative parallax is a
real measurement, not a structural error).

### Helpers

- `has_sky_position` — `ra_deg` and `dec_deg` both present.
- `has_cartesian` — `x`, `y`, `z` all present.
- `has_position` — placeable on the sky or in 3D.

### `CANONICAL_UNITS`

A `dict[str, str]` mapping each numeric field to its canonical unit (`deg`,
`pc`, `mas`, `km/s`, `mas/yr`, `mag`, `dimensionless`). The single source of
truth for the unit convention; connectors must convert to it.

## `Dataset`

Metadata *about* a collection of objects (e.g. a JSONL file or a query result) —
not the container of the records.

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `dataset_id` | str | — | Stable unique id (non-empty). |
| `name` | str | — | Human-readable name. |
| `source` | str | — | Originating service/catalog. |
| `description` | str | `""` | |
| `object_count` | int | `0` | `>= 0`. |
| `created_at` | datetime | now (UTC) | |
| `query_parameters` | dict | `{}` | |
| `coordinate_system` | str | `"ICRS"` | |
| `units` | dict | `CANONICAL_UNITS` | |
| `provenance` | `Provenance`? | `None` | |

`Dataset.from_objects(objects, *, dataset_id, name, source, **kwargs)` builds a
description and fills `object_count`.

## JSONL interchange (`unav_core.data.io`)

One JSON object per line, UTF-8; datetimes as ISO-8601; `NaN`/`inf` rejected.

```python
from unav_core.data import CatalogObject, ObjectType, read_jsonl, write_jsonl

objs = [CatalogObject(uid="gaia:5853498713160606720", native_id="5853498713160606720",
                      source="Gaia DR3", object_type=ObjectType.STAR,
                      ra_deg=279.23, dec_deg=38.78)]
write_jsonl(objs, "stars.jsonl")     # -> number written
restored = read_jsonl("stars.jsonl") # -> list[CatalogObject]
```

- `write_jsonl(objects, path) -> int` — writes JSONL, creating parent dirs.
- `read_jsonl(path) -> list[CatalogObject]` — raises `ValueError` (with line
  context) on the first bad line.
- `validate_jsonl(path) -> ValidationReport` — inspects a file **without**
  raising; see [PROVENANCE_AND_VALIDATION](PROVENANCE_AND_VALIDATION.md).

Example line:

```json
{"uid": "gaia:5853498713160606720", "source": "Gaia DR3", "object_type": "star", "name": "Vega", "native_id": "5853498713160606720", "ra_deg": 279.23, "dec_deg": 38.78, "parallax_mas": 130.23, "metadata": {}, "provenance": null}
```
