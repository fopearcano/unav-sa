"""Local persistence, cache and spatial queries.

Provides the on-disk **local cache** and query layer (SQLAlchemy 2.x over a
SQLite baseline by default). Responsibilities:

* cache catalog records retrieved by connectors, together with their provenance;
* serve **spatial queries** (cone / box / region lookups) against cached data
  using an appropriate spatial index;
* keep the working set local so navigation is real-time and offline-friendly.

The cache is a bounded *working set*, not a full survey mirror.
"""
