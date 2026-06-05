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
from unav_core.db.planning import (
    delete_bookmark,
    delete_mission,
    delete_route,
    get_bookmark,
    get_mission,
    get_route,
    list_bookmarks,
    list_missions,
    list_routes,
    save_bookmark,
    save_mission,
    save_route,
)
from unav_core.db.queries import (
    brightest_objects,
    filter_by_source,
    filter_by_type,
    get_object,
    highest_redshift_objects,
    nearest_objects,
    objects_in_sky_box,
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
    "objects_in_sky_box",
    "brightest_objects",
    "highest_redshift_objects",
    "cone_search",
    "angular_separation_deg",
    "save_bookmark",
    "list_bookmarks",
    "get_bookmark",
    "delete_bookmark",
    "save_route",
    "list_routes",
    "get_route",
    "delete_route",
    "save_mission",
    "list_missions",
    "get_mission",
    "delete_mission",
]
