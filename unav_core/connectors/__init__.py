"""Data-source connectors.

Home for connectors to real astronomical data sources. Each connector translates
a normalised UNAV query (typically a *regional* query) into a source-specific
request and maps the response back onto the canonical :mod:`unav_core.data`
schema, attaching :mod:`unav_core.provenance` records.

Design rules:

* **Regional / bounded queries only** — never bulk-download whole catalogs.
* Results flow through validation and provenance before reaching callers.
* astroquery / pyvo are *optional* dependencies, imported lazily — importing a
  connector module never requires them.

Implemented: **Gaia DR3** (:mod:`unav_core.connectors.gaia`), **NASA/JPL
Horizons** (:mod:`unav_core.connectors.jpl`), **SDSS**
(:mod:`unav_core.connectors.sdss`) and a conservative **DESI** foundation
(:mod:`unav_core.connectors.desi`). SIMBAD, VizieR and MAST are future work.
See ``docs/DATA_SOURCE_STRATEGY.md``.
"""

from unav_core.connectors.base import (
    AstroqueryNotInstalledError,
    ConnectorError,
    ConnectorNetworkError,
    ConnectorNotSupportedError,
    EmptyResultError,
    MalformedResponseError,
    astroquery_available,
)
from unav_core.connectors.desi import (
    fetch_desi_region,
    load_desi_file,
    normalize_desi_rows,
)
from unav_core.connectors.gaia import fetch_gaia_region
from unav_core.connectors.jpl import fetch_jpl_body, fetch_jpl_solar_system
from unav_core.connectors.sdss import fetch_sdss_region, normalize_sdss_rows

__all__ = [
    "fetch_gaia_region",
    "fetch_jpl_body",
    "fetch_jpl_solar_system",
    "fetch_sdss_region",
    "normalize_sdss_rows",
    "fetch_desi_region",
    "load_desi_file",
    "normalize_desi_rows",
    "astroquery_available",
    "ConnectorError",
    "AstroqueryNotInstalledError",
    "ConnectorNetworkError",
    "EmptyResultError",
    "MalformedResponseError",
    "ConnectorNotSupportedError",
]
