"""Persistence models for the local database (aggregation / discoverability hub).

The canonical definitions live in their focused modules — this module re-exports
them so the DB-layer "models" can be found in one place:

* the SQLite tables and the row ↔ object mapping → :mod:`unav_core.db.schema`;
* the :class:`~unav_core.db.database.Database` handle → :mod:`unav_core.db.database`;
* the :class:`~unav_core.db.importer.ImportSummary` → :mod:`unav_core.db.importer`.

The domain models a row maps to/from (``CatalogObject``, ``Dataset``,
``Provenance``) live in :mod:`unav_core.data` / :mod:`unav_core.provenance` and are
re-exported here for convenience. See ``docs/SQLITE_SCHEMA.md`` and
``docs/LOCAL_DATABASE.md``.
"""

from __future__ import annotations

from unav_core.data.dataset import Dataset
from unav_core.data.schema import CatalogObject
from unav_core.db.database import Database
from unav_core.db.importer import ImportSummary
from unav_core.db.schema import (
    bookmarks_table,
    datasets_table,
    metadata_obj,
    metadata_table,
    missions_table,
    object_core_values,
    objects_table,
    provenance_table,
    routes_table,
    row_to_object,
)
from unav_core.provenance.provenance import Provenance

#: All tables in the local-cache schema (keyed by table name).
TABLES = {
    "objects": objects_table,
    "metadata": metadata_table,
    "datasets": datasets_table,
    "provenance": provenance_table,
    "bookmarks": bookmarks_table,
    "routes": routes_table,
    "missions": missions_table,
}

__all__ = [
    # handle + summary
    "Database",
    "ImportSummary",
    # tables + mapping
    "metadata_obj",
    "objects_table",
    "metadata_table",
    "datasets_table",
    "provenance_table",
    "bookmarks_table",
    "routes_table",
    "missions_table",
    "TABLES",
    "object_core_values",
    "row_to_object",
    # domain models a row maps to/from
    "CatalogObject",
    "Dataset",
    "Provenance",
]
