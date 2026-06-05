"""Import normalized catalog objects (and JSONL files) into the local cache.

``import_jsonl_to_db`` reads a JSONL file resiliently (recording parse/validation
errors rather than aborting), de-duplicates by ``uid`` both within the file and
against existing rows, inserts the new objects, records a ``dataset`` and its
``provenance``, and returns an :class:`ImportSummary`.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from unav_core.data.dataset import Dataset
from unav_core.data.schema import CatalogObject
from unav_core.db.database import Database, PathLike
from unav_core.db.schema import (
    datasets_table,
    metadata_table,
    object_core_values,
    objects_table,
    provenance_table,
)
from unav_core.provenance.provenance import Provenance

_EXISTS_CHUNK = 500


class ImportSummary(BaseModel):
    """Outcome of an import operation."""

    dataset_id: str
    dataset_name: str
    source: str
    objects_read: int = 0
    parse_errors: int = 0
    duplicates_in_file: int = 0
    duplicates_existing: int = 0
    inserted: int = 0
    error_details: list[str] = Field(default_factory=list)

    def render(self) -> str:
        """Return a human-readable, multi-line summary."""
        return "\n".join(
            [
                f"Dataset '{self.dataset_name}' (id={self.dataset_id}, source={self.source})",
                f"  objects read:        {self.objects_read}",
                f"  parse errors:        {self.parse_errors}",
                f"  duplicates in file:  {self.duplicates_in_file}",
                f"  already in database: {self.duplicates_existing}",
                f"  inserted:            {self.inserted}",
            ]
        )


def import_objects(
    db: Database,
    objects: Sequence[CatalogObject],
    *,
    dataset_name: str,
    query_parameters: dict | None = None,
    parse_errors: Sequence[str] | None = None,
) -> ImportSummary:
    """Insert ``objects`` into ``db`` and record the dataset + provenance."""
    query_parameters = dict(query_parameters or {})
    parse_errors = list(parse_errors or [])

    seen: set[str] = set()
    unique: list[CatalogObject] = []
    duplicates_in_file = 0
    for obj in objects:
        if obj.uid in seen:
            duplicates_in_file += 1
            continue
        seen.add(obj.uid)
        unique.append(obj)

    existing = _existing_uids(db, [obj.uid for obj in unique])
    to_insert = [obj for obj in unique if obj.uid not in existing]
    duplicates_existing = len(unique) - len(to_insert)

    sources = {obj.source for obj in unique}
    if len(sources) == 1:
        source = next(iter(sources))
    elif sources:
        source = "mixed"
    else:
        source = dataset_name

    dataset_id = uuid.uuid4().hex
    dataset = Dataset(
        dataset_id=dataset_id,
        name=dataset_name,
        source=source,
        object_count=len(to_insert),
        query_parameters=query_parameters,
        provenance=Provenance.now(
            source,
            endpoint=query_parameters.get("jsonl_path"),
            query_parameters=query_parameters,
        ),
    )

    with db.begin() as conn:
        if to_insert:
            conn.execute(objects_table.insert(), [object_core_values(obj) for obj in to_insert])
            metadata_rows = [
                {
                    "uid": obj.uid,
                    "metadata_json": json.dumps(obj.metadata, ensure_ascii=False, allow_nan=False),
                }
                for obj in to_insert
                if obj.metadata
            ]
            if metadata_rows:
                conn.execute(metadata_table.insert(), metadata_rows)
        conn.execute(
            datasets_table.insert(),
            {
                "dataset_id": dataset_id,
                "name": dataset.name,
                "source": dataset.source,
                "object_count": dataset.object_count,
                "created_at": dataset.created_at.isoformat(),
                "query_parameters_json": json.dumps(query_parameters, ensure_ascii=False),
            },
        )
        conn.execute(
            provenance_table.insert(),
            {
                "dataset_id": dataset_id,
                "provenance_json": json.dumps(
                    dataset.provenance.model_dump(mode="json") if dataset.provenance else {},
                    ensure_ascii=False,
                ),
            },
        )

    return ImportSummary(
        dataset_id=dataset_id,
        dataset_name=dataset_name,
        source=source,
        objects_read=len(list(objects)),
        parse_errors=len(parse_errors),
        duplicates_in_file=duplicates_in_file,
        duplicates_existing=duplicates_existing,
        inserted=len(to_insert),
        error_details=parse_errors[:50],
    )


def import_jsonl_to_db(
    jsonl_path: PathLike,
    db_path: PathLike,
    dataset_name: str,
    *,
    enrich: bool = False,
    database: Database | None = None,
) -> ImportSummary:
    """Import a JSONL catalog file into a SQLite database.

    Parameters mirror the CLI: ``jsonl_path`` is the input file, ``db_path`` the
    SQLite database, and ``dataset_name`` labels the import. When ``enrich`` is
    true, each object's Cartesian ``x/y/z`` is computed (Astropy) before storage.
    Pass an open ``database`` to import into an existing (e.g. in-memory) handle.
    """
    objects, errors = _read_objects(jsonl_path)
    if enrich:
        from unav_core.astro.enrich import enrich_object_coordinates

        objects = [enrich_object_coordinates(obj) for obj in objects]

    owns_database = database is None
    db = database if database is not None else Database(db_path)
    try:
        return import_objects(
            db,
            objects,
            dataset_name=dataset_name,
            query_parameters={
                "jsonl_path": str(jsonl_path),
                "dataset_name": dataset_name,
                "enrich": enrich,
            },
            parse_errors=errors,
        )
    finally:
        if owns_database:
            db.dispose()


def _read_objects(path: PathLike) -> tuple[list[CatalogObject], list[str]]:
    objects: list[CatalogObject] = []
    errors: list[str] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                data = json.loads(text)
            except json.JSONDecodeError as exc:
                errors.append(f"line {lineno}: invalid JSON: {exc}")
                continue
            try:
                objects.append(CatalogObject.model_validate(data))
            except ValidationError:
                errors.append(f"line {lineno}: schema validation failed")
    return objects, errors


def _existing_uids(db: Database, uids: Sequence[str]) -> set[str]:
    found: set[str] = set()
    if not uids:
        return found
    cols = objects_table.c
    from sqlalchemy import select

    with db.connect() as conn:
        for start in range(0, len(uids), _EXISTS_CHUNK):
            chunk = uids[start : start + _EXISTS_CHUNK]
            rows = conn.execute(select(cols.uid).where(cols.uid.in_(chunk)))
            found.update(row[0] for row in rows)
    return found
