"""Catalog schema, data models and record validation.

Defines the canonical, *source-independent* representation of astronomical
objects and catalog records (pydantic models), together with the query/region
request models used by spatial queries. This is where **catalog schema** and
**validation** live: every record entering the system is normalised and
validated against these models regardless of which connector produced it.

This package does not fetch data (see :mod:`unav_core.connectors`) or persist it
(see :mod:`unav_core.db`).
"""

from unav_core.data.dataset import Dataset
from unav_core.data.io import read_jsonl, validate_jsonl, write_jsonl
from unav_core.data.object_types import ObjectType
from unav_core.data.schema import CANONICAL_UNITS, CatalogObject

__all__ = [
    "CatalogObject",
    "Dataset",
    "ObjectType",
    "CANONICAL_UNITS",
    "read_jsonl",
    "write_jsonl",
    "validate_jsonl",
]
