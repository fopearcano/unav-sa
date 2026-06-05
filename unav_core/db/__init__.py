"""Local persistence, cache and spatial queries.

Provides the on-disk **local cache** and query layer (SQLAlchemy 2.x over a
SQLite baseline by default). Responsibilities:

* cache catalog records retrieved by connectors, together with their provenance;
* serve **spatial queries** (cone / box / region lookups) against cached data
  using an appropriate spatial index;
* keep the working set local so navigation is real-time and offline-friendly.

The cache is a bounded *working set*, not a full survey mirror.
"""

from unav_core.db.database import Database
from unav_core.db.importer import ImportSummary, import_jsonl_to_db, import_objects
from unav_core.db.queries import (
    brightest_objects,
    filter_by_source,
    filter_by_type,
    get_object,
    highest_redshift_objects,
    nearest_objects,
    objects_within_distance,
    search_by_name,
)
from unav_core.db.spatial import angular_separation_deg, cone_search

__all__ = [
    "Database",
    "ImportSummary",
    "import_jsonl_to_db",
    "import_objects",
    "search_by_name",
    "get_object",
    "filter_by_source",
    "filter_by_type",
    "nearest_objects",
    "objects_within_distance",
    "brightest_objects",
    "highest_redshift_objects",
    "cone_search",
    "angular_separation_deg",
]
