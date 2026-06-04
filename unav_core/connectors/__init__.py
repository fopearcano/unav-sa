"""Data-source connectors (not implemented yet).

Home for connectors to real astronomical data sources — Gaia, SDSS, DESI,
NASA/JPL Horizons, SIMBAD, VizieR, MAST and other Virtual Observatory services.
A connector translates a normalised UNAV query (typically a *regional* query)
into a source-specific request and maps the response back onto the canonical
:mod:`unav_core.data` schema, attaching :mod:`unav_core.provenance` records.

Design rules:

* **Regional / bounded queries only** — never bulk-download whole catalogs.
* Results flow through validation and provenance before reaching callers.
* astroquery / pyvo are *optional* dependencies, imported lazily.

See ``docs/DATA_SOURCE_STRATEGY.md``. No fetching logic is implemented at this
stage of the project.
"""
