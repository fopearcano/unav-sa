# UNAV-SA — Provenance & Validation

How UNAV-SA records **where data came from** and how it **validates** records.
Implemented in `unav_core.provenance` (Phase 1; pure data, no Astropy).

## Provenance

`Provenance` captures enough to reproduce and audit any result. It is attached
to records (and datasets) and travels with them through cache, navigation and
export.

| Field | Type | Notes |
| --- | --- | --- |
| `source` | str | Originating service, e.g. `"Gaia"` (non-empty). |
| `catalog` | str? | Catalog/release, e.g. `"Gaia DR3"`. |
| `version` | str? | Version identifier. |
| `reference_frame` | str? | e.g. `"ICRS"`, `"Galactic"`. |
| `epoch` | str? | Reference epoch, e.g. `"J2016.0"`. |
| `query_parameters` | dict | The exact query (region, filters, row limit, ...). |
| `units` | dict | Unit assumptions (`field -> unit`). |
| `endpoint` | str? | Service endpoint/URL used. |
| `retrieved_at` | datetime? | UTC retrieval timestamp. |
| `notes` | str? | Free-form notes. |

`Provenance.now(source, **kwargs)` stamps `retrieved_at` with the current UTC
time.

```python
from unav_core.provenance import Provenance
prov = Provenance.now("Gaia", catalog="Gaia DR3", reference_frame="ICRS",
                      query_parameters={"ra": 279.2, "dec": 38.8, "radius_deg": 0.1})
```

## Two-tier validation

UNAV-SA separates **structural** validity from **semantic / quality** checks so
that real-but-imperfect data can be ingested and *reported* rather than silently
dropped (per [`DATA_SOURCE_STRATEGY.md`](DATA_SOURCE_STRATEGY.md)).

1. **Structural** — enforced by the Pydantic models at construction time (types,
   finite numbers, coordinate ranges, non-empty ids, no unknown fields). A
   structural failure raises immediately.
2. **Semantic / quality** — performed by the helpers below on already
   constructed objects. They **never raise**; they return structured issues.

### Severities

- `ERROR` — the record cannot be trusted or placed.
- `WARNING` — the value is real but limited.

The distinction matters: a **non-positive parallax** is a *warning*, because
Gaia genuinely reports negative parallaxes from measurement noise — they are
valid data that simply cannot be inverted to a distance. Discarding them would
lose real measurements, so UNAV-SA keeps and flags them.

### Helpers (`unav_core.provenance.validation`)

| Function | Issue code | Severity | Trigger |
| --- | --- | --- | --- |
| `detect_missing_coordinates(obj)` | `missing_coordinates` | ERROR | No `ra+dec` and no `x,y,z`. |
| `detect_invalid_parallax(obj)` | `invalid_parallax` | WARNING | `parallax_mas <= 0`. |
| `detect_invalid_redshift(obj)` | `invalid_redshift` | ERROR | `redshift <= -1` (1 + z must be > 0). |
| `detect_malformed_metadata(obj)` | `malformed_metadata` | ERROR | Non-dict, non-string keys, or not JSON-serialisable (incl. `NaN`/`inf`). |
| `detect_duplicate_uids(objects)` | `duplicate_uid` | ERROR | A `uid` appears more than once (see below). |

Each per-object detector returns `ValidationIssue | None`;
`detect_duplicate_uids` returns a `list[ValidationIssue]`.

**`uid` is global, so duplicate detection is global.** A `uid` is the
[globally unique UNAV id](CORE_DATA_SCHEMA.md#identity-uid--native_id), not a
per-source id — so two records sharing a `uid` are a collision **even across
different sources/datasets**, and are flagged as an ERROR. Source-native ids
(which are only unique *within* a catalog) belong in `native_id` or `metadata`,
never in `uid` alone; this is what keeps merged datasets collision-free.

### Aggregation

- `validate_object(obj) -> ValidationReport` — runs all per-object detectors.
- `validate_objects(objects) -> ValidationReport` — per-object detectors over a
  collection **plus** duplicate-uid detection.

### `ValidationReport`

- `issues: list[ValidationIssue]`
- `ok` — `True` when there are **no** `ERROR`s (warnings are allowed).
- `errors`, `warnings` — filtered views.
- `add(issue)`, `extend(issues)`, `len(report)`.

`ValidationIssue` carries `code`, `severity`, `message`, and optional `uid` and
`field`.

```python
from unav_core.data import CatalogObject, ObjectType
from unav_core.provenance import validate_objects

objs = [CatalogObject(uid="a", source="Gaia", object_type=ObjectType.STAR,
                      ra_deg=10.0, dec_deg=20.0, parallax_mas=-0.4)]
report = validate_objects(objs)
report.ok          # True  -> only a WARNING (negative parallax)
report.warnings    # [ValidationIssue(code="invalid_parallax", ...)]
```

## File validation

`unav_core.data.io.validate_jsonl(path)` reuses these helpers to validate a
JSONL file without importing it, additionally reporting `json_error` and
`schema_error` (with line numbers) for lines that fail to parse or fail
structural validation. See [`CORE_DATA_SCHEMA.md`](CORE_DATA_SCHEMA.md).
