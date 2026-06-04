"""UNAV-SA core: the standalone, DCC-independent astronomical navigation engine.

``unav_core`` is the heart of UNAV-SA. It owns *all* astronomy and data logic:

* coordinates, time and units      (:mod:`unav_core.astro`)
* catalog schema and validation    (:mod:`unav_core.data`)
* data-source connectors           (:mod:`unav_core.connectors`)
* local cache and spatial queries  (:mod:`unav_core.db`)
* navigation state                 (:mod:`unav_core.navigation`)
* routes and missions              (:mod:`unav_core.routes`, :mod:`unav_core.missions`)
* export / interchange             (:mod:`unav_core.export`)
* provenance                       (:mod:`unav_core.provenance`)

Architectural rules:

* This package MUST stay independent from any DCC (Cinema 4D, Blender,
  Houdini, Unreal). DCC integrations are downstream *adapters*.
* Heavy scientific dependencies (astropy, and optionally astroquery/pyvo)
  belong here and in the standalone app/server — never inside a DCC runtime.
* ``import unav_core`` is cheap and side-effect free: submodules import their
  dependencies lazily and perform no network I/O at import time.

See ``docs/UNAV_SA_ARCHITECTURE.md`` for the full design.
"""

__version__ = "0.0.1"

__all__ = ["__version__"]
