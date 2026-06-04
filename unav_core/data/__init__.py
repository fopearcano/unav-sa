"""Catalog schema, data models and record validation.

Defines the canonical, *source-independent* representation of astronomical
objects and catalog records (pydantic models), together with the query/region
request models used by spatial queries. This is where **catalog schema** and
**validation** live: every record entering the system is normalised and
validated against these models regardless of which connector produced it.

This package does not fetch data (see :mod:`unav_core.connectors`) or persist it
(see :mod:`unav_core.db`).
"""
