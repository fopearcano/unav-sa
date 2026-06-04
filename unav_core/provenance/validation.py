"""Semantic and collection-level validation helpers.

These operate on *already constructed*
:class:`~unav_core.data.schema.CatalogObject` instances — structural validity
(types, finite numbers, coordinate ranges) is enforced by the model itself.
The helpers never raise: each returns structured :class:`ValidationIssue`
results so the ingest layer can decide whether to reject or quarantine a record
(per ``docs/DATA_SOURCE_STRATEGY.md``).

Severity convention:

* ``ERROR``   — the record cannot be trusted or placed (missing coordinates,
  unphysical redshift, malformed metadata, duplicate uid).
* ``WARNING`` — the value is real but limited. A non-positive parallax, for
  example, is a genuine Gaia measurement that simply cannot yield a distance;
  it is flagged, not discarded.

See ``docs/PROVENANCE_AND_VALIDATION.md``.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable
from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:  # import only for typing — avoids a runtime cycle with data.schema
    from unav_core.data.schema import CatalogObject


class Severity(str, Enum):
    """Severity of a :class:`ValidationIssue`."""

    ERROR = "error"
    WARNING = "warning"


class ValidationIssue(BaseModel):
    """A single problem found with a record or a collection."""

    code: str
    severity: Severity
    message: str
    uid: str | None = None
    field: str | None = None


class ValidationReport(BaseModel):
    """A collection of :class:`ValidationIssue` results."""

    issues: list[ValidationIssue] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True when there are no ERROR-severity issues (warnings are allowed)."""
        return not any(issue.severity == Severity.ERROR for issue in self.issues)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == Severity.WARNING]

    def add(self, issue: ValidationIssue) -> None:
        self.issues.append(issue)

    def extend(self, issues: Iterable[ValidationIssue]) -> None:
        self.issues.extend(issues)

    def __len__(self) -> int:
        return len(self.issues)


def detect_missing_coordinates(obj: CatalogObject) -> ValidationIssue | None:
    """Flag objects that can be placed neither on the sky nor in 3D space."""
    if obj.has_position:
        return None
    return ValidationIssue(
        code="missing_coordinates",
        severity=Severity.ERROR,
        message="object has neither a complete sky position (ra+dec) nor cartesian (x,y,z)",
        uid=obj.uid,
        field="ra_deg",
    )


def detect_invalid_parallax(obj: CatalogObject) -> ValidationIssue | None:
    """Flag non-positive parallaxes (real measurements, but no usable distance)."""
    if obj.parallax_mas is not None and obj.parallax_mas <= 0.0:
        return ValidationIssue(
            code="invalid_parallax",
            severity=Severity.WARNING,
            message="non-positive parallax cannot yield a positive distance",
            uid=obj.uid,
            field="parallax_mas",
        )
    return None


def detect_invalid_redshift(obj: CatalogObject) -> ValidationIssue | None:
    """Flag unphysical redshifts (1 + z must be > 0, so z <= -1 is invalid)."""
    if obj.redshift is not None and obj.redshift <= -1.0:
        return ValidationIssue(
            code="invalid_redshift",
            severity=Severity.ERROR,
            message="redshift <= -1 is unphysical (1 + z must be > 0)",
            uid=obj.uid,
            field="redshift",
        )
    return None


def detect_malformed_metadata(obj: CatalogObject) -> ValidationIssue | None:
    """Flag metadata that is not a JSON-serialisable mapping with string keys."""
    metadata = obj.metadata
    if not isinstance(metadata, dict):
        return ValidationIssue(
            code="malformed_metadata",
            severity=Severity.ERROR,
            message="metadata must be a dict",
            uid=obj.uid,
            field="metadata",
        )
    bad_keys = [key for key in metadata if not isinstance(key, str)]
    if bad_keys:
        return ValidationIssue(
            code="malformed_metadata",
            severity=Severity.ERROR,
            message=f"metadata keys must be strings; offending keys: {bad_keys!r}",
            uid=obj.uid,
            field="metadata",
        )
    try:
        json.dumps(metadata, allow_nan=False)
    except (TypeError, ValueError) as exc:
        return ValidationIssue(
            code="malformed_metadata",
            severity=Severity.ERROR,
            message=f"metadata is not JSON-serialisable: {exc}",
            uid=obj.uid,
            field="metadata",
        )
    return None


_PER_OBJECT_DETECTORS = (
    detect_missing_coordinates,
    detect_invalid_parallax,
    detect_invalid_redshift,
    detect_malformed_metadata,
)


def detect_duplicate_uids(objects: Iterable[CatalogObject]) -> list[ValidationIssue]:
    """Flag any uid that appears more than once in the collection."""
    counts = Counter(obj.uid for obj in objects)
    issues: list[ValidationIssue] = []
    for uid, count in counts.items():
        if count > 1:
            issues.append(
                ValidationIssue(
                    code="duplicate_uid",
                    severity=Severity.ERROR,
                    message=f"uid appears {count} times in the collection",
                    uid=uid,
                    field="uid",
                )
            )
    return issues


def validate_object(obj: CatalogObject) -> ValidationReport:
    """Run all per-object detectors and collect the issues."""
    report = ValidationReport()
    for detector in _PER_OBJECT_DETECTORS:
        issue = detector(obj)
        if issue is not None:
            report.add(issue)
    return report


def validate_objects(objects: Iterable[CatalogObject]) -> ValidationReport:
    """Run per-object detectors over a collection and add duplicate-uid checks."""
    report = ValidationReport()
    materialised = list(objects)
    for obj in materialised:
        report.extend(validate_object(obj).issues)
    report.extend(detect_duplicate_uids(materialised))
    return report
