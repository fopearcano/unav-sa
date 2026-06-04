"""JSONL import/export for :class:`~unav_core.data.schema.CatalogObject` records.

One JSON object per line, UTF-8. Datetimes are serialised as ISO-8601 strings
and NaN/inf are rejected (``allow_nan=False``) so the output is always valid
JSON. This is a simple, human-inspectable interchange format for the local cache
and for fixtures; it is not a connector (no network I/O).
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from pathlib import Path

from pydantic import ValidationError

from unav_core.data.schema import CatalogObject
from unav_core.provenance.validation import (
    Severity,
    ValidationIssue,
    ValidationReport,
    validate_objects,
)

PathLike = str | Path


def write_jsonl(objects: Iterable[CatalogObject], path: PathLike) -> int:
    """Write ``objects`` to ``path`` as JSONL. Returns the number written.

    Parent directories are created as needed. Assumes the objects are valid;
    NaN/inf (e.g. inside metadata) raise rather than emit invalid JSON.
    """
    target = Path(path)
    if target.parent and not target.parent.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with target.open("w", encoding="utf-8") as handle:
        for obj in objects:
            payload = obj.model_dump(mode="json")
            handle.write(json.dumps(payload, ensure_ascii=False, allow_nan=False))
            handle.write("\n")
            count += 1
    return count


def read_jsonl(path: PathLike) -> list[CatalogObject]:
    """Read a JSONL file into objects.

    Raises ``ValueError`` (with file/line context) on the first malformed or
    invalid line. Use :func:`validate_jsonl` to inspect a file without raising.
    """
    objects: list[CatalogObject] = []
    for lineno, raw in _iter_nonblank_lines(path):
        try:
            objects.append(CatalogObject.model_validate(json.loads(raw)))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ValueError(f"{path}:{lineno}: {exc}") from exc
    return objects


def validate_jsonl(path: PathLike) -> ValidationReport:
    """Validate a JSONL file without importing it. Never raises on bad content.

    Reports both structural problems (``json_error``, ``schema_error`` with line
    numbers) and the semantic / duplicate-uid issues from
    :func:`~unav_core.provenance.validation.validate_objects`.
    """
    report = ValidationReport()
    parsed: list[CatalogObject] = []
    for lineno, raw in _iter_nonblank_lines(path):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            report.add(
                ValidationIssue(
                    code="json_error",
                    severity=Severity.ERROR,
                    message=f"line {lineno}: invalid JSON: {exc}",
                )
            )
            continue
        try:
            parsed.append(CatalogObject.model_validate(data))
        except ValidationError as exc:
            uid = data.get("uid") if isinstance(data, dict) else None
            report.add(
                ValidationIssue(
                    code="schema_error",
                    severity=Severity.ERROR,
                    message=f"line {lineno}: {exc}",
                    uid=uid if isinstance(uid, str) else None,
                )
            )
            continue
    report.extend(validate_objects(parsed).issues)
    return report


def _iter_nonblank_lines(path: PathLike) -> Iterator[tuple[int, str]]:
    with Path(path).open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle, start=1):
            stripped = line.strip()
            if stripped:
                yield index, stripped
