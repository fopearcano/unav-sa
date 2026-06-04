"""Missions: saved navigation sessions and scenarios.

Models **missions** — higher-level, persistable scenarios that compose one or
more :mod:`unav_core.routes`, target sets, timing and navigation parameters into
a reproducible session. Missions are serialisable via :mod:`unav_core.export`
and carry provenance for the data they reference.
"""
