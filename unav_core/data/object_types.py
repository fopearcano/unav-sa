"""Canonical astronomical object-type taxonomy.

A small, source-independent enumeration that every
:class:`~unav_core.data.schema.CatalogObject` is classified with. Connectors map
a source's native type strings onto these members via :meth:`ObjectType.coerce`,
falling back to :attr:`ObjectType.UNKNOWN` for anything unrecognised (and
:attr:`ObjectType.CUSTOM` for deliberately caller-defined types).
"""

from __future__ import annotations

from enum import Enum


class ObjectType(str, Enum):
    """Type of an astronomical (or human-made) object tracked by UNAV-SA."""

    STAR = "star"
    GALAXY = "galaxy"
    QUASAR = "quasar"
    PLANET = "planet"
    MOON = "moon"
    ASTEROID = "asteroid"
    COMET = "comet"
    SPACECRAFT = "spacecraft"
    NEBULA = "nebula"
    CUSTOM = "custom"
    UNKNOWN = "unknown"

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return self.value

    @classmethod
    def coerce(cls, value: object) -> ObjectType:
        """Best-effort mapping of an arbitrary value onto an :class:`ObjectType`.

        Matching is case-insensitive and ignores surrounding whitespace. Returns
        :attr:`UNKNOWN` for ``None`` or any unrecognised value.
        """
        if isinstance(value, cls):
            return value
        if value is None:
            return cls.UNKNOWN
        try:
            return cls(str(value).strip().lower())
        except ValueError:
            return cls.UNKNOWN
