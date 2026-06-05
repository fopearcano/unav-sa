# UNAV-SA — JSONL Catalog Format

UNAV-SA's plain-text interchange format for catalogs: **one
`CatalogObject` per line**, as JSON, UTF-8. It is the format the sample generator
writes, the importer reads, and tests use as fixtures — simple, diffable, and
human-inspectable. Implemented in `unav_core.data.io`.

> See [`CORE_DATA_SCHEMA.md`](CORE_DATA_SCHEMA.md) for the record schema and
> [`PROVENANCE_AND_VALIDATION.md`](PROVENANCE_AND_VALIDATION.md) for validation.

## The format

- **One object per line.** Each line is a complete JSON object — a serialised
  [`CatalogObject`](CORE_DATA_SCHEMA.md) (`obj.model_dump(mode="json")`).
- **UTF-8**, `ensure_ascii=False` (non-ASCII names are written as-is).
- **No NaN/Inf.** Serialisation uses `allow_nan=False`, so the output is always
  strictly valid JSON; a non-finite value (e.g. inside `metadata`) raises rather
  than emitting `NaN`.
- **Datetimes are ISO-8601 strings** (e.g. `provenance.retrieved_at`).
- **Deterministic field order.** Fields are emitted in the model's declaration
  order, so the same objects produce byte-identical output (handy for diffs and
  reproducible fixtures).
- **Blank lines are ignored** on read. There is no header line and no trailing
  metadata — the file *is* the list of objects.
- **Extension:** `.jsonl` by convention (the API does not enforce it).

### Example (two lines, abridged)

```json
{"uid": "SAMPLE-00001-STAR", "source": "sample-gaia", "object_type": "star", "name": "Sample Star 1", "ra_deg": 230.19, "dec_deg": -85.49, "distance_pc": 138.24, "parallax_mas": 7.23, "x": -6.94, "y": -8.33, "z": -137.81, "metadata": {"sample": true}, "provenance": {"source": "sample-gaia", "reference_frame": "ICRS", "epoch": "J2000.0"}}
{"uid": "SAMPLE-00051-GAL", "source": "sample-sdss", "object_type": "galaxy", "name": "Sample Galaxy 1", "ra_deg": 12.34, "dec_deg": 5.67, "redshift": 0.17, "metadata": {"sample": true}, "provenance": {"source": "sample-sdss"}}
```

Each line is independent: galaxies carry a redshift and no distance; stars carry a
distance/parallax. Optional fields that are unset are still present as `null`
(pydantic emits all declared fields).

Every line's `uid` is the
[globally unique UNAV id](CORE_DATA_SCHEMA.md#identity-uid--native_id) — normally
source-prefixed (e.g. `gaia:5853498713160606720`) — with the source-native id in
`native_id`. A catalog must not contain duplicate `uid`s (`validate_jsonl` reports
them as errors), even when it merges records from several sources.

## API (`unav_core.data.io`)

| Function | Behaviour |
| --- | --- |
| `write_jsonl(objects, path) -> int` | Write objects (one per line); create parent dirs; return the count. Non-finite values raise. |
| `read_jsonl(path) -> list[CatalogObject]` | Parse + validate every line. Raises `ValueError` with **`path:line`** context on the first malformed/invalid line. |
| `validate_jsonl(path) -> ValidationReport` | Inspect a file **without** importing it; never raises. Reports per-line `json_error` / `schema_error` plus the semantic and duplicate-uid issues from [`validation`](PROVENANCE_AND_VALIDATION.md). |

```python
from pathlib import Path
from unav_core.data import write_jsonl, read_jsonl, validate_jsonl

write_jsonl(objects, Path("data/catalogs/my_catalog.jsonl"))
restored = read_jsonl("data/catalogs/my_catalog.jsonl")   # raises on bad lines
report = validate_jsonl("data/catalogs/my_catalog.jsonl")  # never raises
if not report.ok:
    for issue in report.errors:
        print(issue.code, issue.uid, issue.message)
```

All three accept `str` **or** `pathlib.Path`. None of them touch the network — JSONL
is a local interchange format, not a connector.

## Rules & guarantees

- **`read_jsonl` fails fast and clearly:** the first bad line aborts the read with
  `"<path>:<lineno>: <reason>"` (invalid JSON *or* schema validation error). Use
  `validate_jsonl` when you want to collect *all* problems instead of stopping.
- **Round-trip is lossless** for valid records: `read_jsonl(write_jsonl(objs))`
  reconstructs equal objects (modulo the canonical ISO datetime form).
- **Structural validity is the model's job;** `read_jsonl` rejects records that
  violate the schema (e.g. `ra_deg` out of `[0, 360)`). Semantic quality
  (missing coordinates, non-positive parallax, …) is *reported* by
  `validate_jsonl`, not rejected — real-but-imperfect survey data still ingests.

## Why JSONL (not CSV or one big JSON array)

- **Streamable / append-friendly:** process or append a line at a time without
  loading the whole file or rewriting an array.
- **Diff-friendly:** one object per line keeps version-control diffs readable.
- **Schema-rich:** nested `metadata`/`provenance` and `null`s are native to JSON
  (CSV cannot represent them cleanly).
- **Self-describing:** every line is the full canonical record — no column header
  to keep in sync with the schema.

Curated example catalogs live under `samples/`; downloaded/working catalogs live
under the git-ignored `data/` (see [`LOCAL_DATABASE.md`](LOCAL_DATABASE.md) and
[`DATA_FETCHING_SAFETY.md`](DATA_FETCHING_SAFETY.md)).
