# UNAV-SA — Database Import Workflow

How normalized `CatalogObject`s get from a JSONL catalog into the local SQLite
database. Implemented in `unav_core.db.importer`; driven by
`tools/import_catalog.py`.

```
 JSONL catalog ─▶ read + validate ─▶ (enrich x/y/z) ─▶ de-duplicate ─▶ insert ─▶ ImportSummary
   (one obj/line)   CatalogObject       Astropy            by uid        objects/   inserted/dup/…
                                                                          metadata/
                                                                          datasets/provenance
```

> Prereq: a normalized JSONL catalog (see
> [`JSONL_CATALOG_FORMAT.md`](JSONL_CATALOG_FORMAT.md)). Schema:
> [`SQLITE_SCHEMA.md`](SQLITE_SCHEMA.md).

## One command

```bash
python tools/import_catalog.py \
  --input samples/sample_catalog.jsonl \
  --db data/unav.db \
  --dataset-name sample [--enrich]
```

The tool initialises the database if missing, imports the JSONL, and prints the
import summary. Inspect afterwards with `python tools/db_info.py --db data/unav.db`.

## API

```python
from unav_core.db import import_jsonl_to_db, import_objects, Database

summary = import_jsonl_to_db("samples/sample_catalog.jsonl", "data/unav.db",
                             "sample", enrich=True)
print(summary.render())

# or, with already-constructed objects and an open handle:
db = Database(":memory:")
summary = import_objects(db, objects, dataset_name="sample")
```

## Behaviour

1. **Resilient read.** Malformed JSON / schema-invalid lines are **recorded** (not
   fatal); valid objects still import. (`import_jsonl_to_db` reads the file;
   `import_objects` takes already-parsed objects.)
2. **Enrichment (optional).** With `enrich=True`, each object's ICRS Cartesian
   `x/y/z` is computed via `unav_core.astro.enrich` before storage — so sky-only
   inputs become 3D-queryable (a parallax-derived distance is flagged in metadata).
3. **De-duplication.** `uid` is the [globally unique id](CORE_DATA_SCHEMA.md#identity-uid--native_id);
   duplicates are removed **within the file** and skipped **against existing rows**,
   deterministically (first occurrence wins). Counts are reported separately.
4. **Metadata stored separately.** Non-empty `metadata` goes in the `metadata`
   table (lazy join on read).
5. **Dataset + provenance recorded.** A `datasets` row (name, source, count, query
   parameters) and a per-dataset `provenance` row are written; each object also
   carries its own provenance in `objects.provenance_json`.

## Import summary

`import_objects` / `import_jsonl_to_db` return an `ImportSummary`:

| Field | Meaning |
| --- | --- |
| `dataset_id`, `dataset_name`, `source` | the recorded dataset |
| `objects_read` | objects seen |
| `parse_errors` | malformed/invalid lines (with `error_details`) |
| `duplicates_in_file` | repeated `uid`s within the input |
| `duplicates_existing` | `uid`s already present in the DB (skipped) |
| `inserted` | rows actually inserted |

`summary.render()` prints a readable multi-line report.

## Not in scope

The importer reads **local** JSONL only — it never fetches from the network.
Producing JSONL from real archives (Gaia/SDSS/DESI/JPL) is a **connector**
concern (Phase 5+); the database is a bounded local working set, not a survey
mirror.
