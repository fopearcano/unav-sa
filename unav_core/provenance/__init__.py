"""Provenance and data-validation records.

Tracks **where every datum came from**: source service, query parameters,
catalog/version identifiers, retrieval timestamps and unit/frame assumptions.
Provenance is attached to records as they enter via :mod:`unav_core.connectors`
and travels with them through cache, navigation and export — making any view or
mission reproducible and auditable.
"""
