"""Provenance and data-validation records.

Tracks **where every datum came from**: source service, query parameters,
catalog/version identifiers, retrieval timestamps and unit/frame assumptions.
Provenance is attached to records as they enter via :mod:`unav_core.connectors`
and travels with them through cache, navigation and export — making any view or
mission reproducible and auditable.

This package also hosts the semantic / collection-level **validation** helpers
(see :mod:`unav_core.provenance.validation`).
"""

from unav_core.provenance.provenance import Provenance
from unav_core.provenance.validation import (
    Severity,
    ValidationIssue,
    ValidationReport,
    detect_duplicate_uids,
    detect_invalid_parallax,
    detect_invalid_redshift,
    detect_malformed_metadata,
    detect_missing_coordinates,
    validate_object,
    validate_objects,
)

__all__ = [
    "Provenance",
    "Severity",
    "ValidationIssue",
    "ValidationReport",
    "validate_object",
    "validate_objects",
    "detect_missing_coordinates",
    "detect_invalid_parallax",
    "detect_invalid_redshift",
    "detect_malformed_metadata",
    "detect_duplicate_uids",
]
