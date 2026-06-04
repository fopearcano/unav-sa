"""Astronomy primitives: coordinates, time and units.

Standardises the astropy-backed building blocks the rest of the core relies on:

* **coordinates** — sky frames (ICRS, Galactic, ecliptic), RA/Dec, proper
  motion, parallax/distance and frame transforms.
* **time** — epochs and time scales (UTC/TT/TDB) and epoch propagation.
* **units** — a single canonical unit registry so every layer speaks the same
  physical units.

Pure primitives only: no catalog access, persistence or navigation logic lives
here. Astropy is imported lazily by submodules so importing this package stays
cheap.
"""
