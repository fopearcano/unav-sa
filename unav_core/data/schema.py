"""The canonical :class:`CatalogObject` schema and the UNAV-SA unit convention.

``CatalogObject`` is the single, source-independent representation every record
is normalised to. Source-specific extras live in :attr:`CatalogObject.metadata`;
origin/audit information lives in :attr:`CatalogObject.provenance`.

The model enforces only *structural* validity: types, finite numbers, and hard
coordinate ranges. Semantic / quality checks (missing coordinates, non-positive
parallax, unphysical redshift, duplicate uids, malformed metadata) live in
:mod:`unav_core.provenance.validation`, so that real-but-imperfect measurements
(e.g. Gaia's genuinely negative parallaxes) can still be ingested and *reported*
rather than silently rejected. See ``docs/CORE_DATA_SCHEMA.md``.
"""

from __future__ import annotations

import math
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from unav_core.data.object_types import ObjectType
from unav_core.provenance.provenance import Provenance

#: Canonical physical unit for each numeric field of :class:`CatalogObject`.
CANONICAL_UNITS: dict[str, str] = {
    "ra_deg": "deg",
    "dec_deg": "deg",
    "distance_pc": "pc",
    "parallax_mas": "mas",
    "redshift": "dimensionless",
    "radial_velocity_kms": "km/s",
    "proper_motion_ra_masyr": "mas/yr",
    "proper_motion_dec_masyr": "mas/yr",
    "apparent_magnitude": "mag",
    "absolute_magnitude": "mag",
    "color_index": "mag",
    "x": "pc",
    "y": "pc",
    "z": "pc",
}

#: Numeric fields constrained to finite (non-NaN/inf) values.
_FLOAT_FIELDS = tuple(CANONICAL_UNITS.keys())


class CatalogObject(BaseModel):
    """A single astronomical object in UNAV-SA's canonical, source-independent schema."""

    model_config = ConfigDict(extra="forbid")

    # --- identity ---
    uid: str = Field(min_length=1, description="Unique id within its source.")
    source: str = Field(min_length=1, description="Originating catalog/service.")
    object_type: ObjectType = Field(description="Canonical object type.")
    name: str | None = Field(default=None, description="Human-readable name/designation.")

    # --- sky position (ICRS, degrees) ---
    ra_deg: float | None = Field(default=None, ge=0.0, lt=360.0, description="RA [0,360) deg.")
    dec_deg: float | None = Field(default=None, ge=-90.0, le=90.0, description="Dec [-90,90] deg.")

    # --- distance / kinematics ---
    distance_pc: float | None = Field(default=None, ge=0.0, description="Distance [pc].")
    parallax_mas: float | None = Field(default=None, description="Parallax [mas]; may be <= 0.")
    redshift: float | None = Field(default=None, description="Redshift z (dimensionless).")
    radial_velocity_kms: float | None = Field(default=None, description="Radial velocity [km/s].")
    proper_motion_ra_masyr: float | None = Field(default=None, description="PM in RA* [mas/yr].")
    proper_motion_dec_masyr: float | None = Field(default=None, description="PM in Dec [mas/yr].")

    # --- photometry ---
    apparent_magnitude: float | None = Field(default=None, description="Apparent magnitude [mag].")
    absolute_magnitude: float | None = Field(default=None, description="Absolute magnitude [mag].")
    color_index: float | None = Field(default=None, description="Colour index [mag].")
    spectral_type: str | None = Field(default=None, description="Spectral type, e.g. 'G2V'.")

    # --- cartesian position [pc] ---
    x: float | None = Field(default=None, description="Cartesian X [pc].")
    y: float | None = Field(default=None, description="Cartesian Y [pc].")
    z: float | None = Field(default=None, description="Cartesian Z [pc].")

    # --- extensibility ---
    metadata: dict[str, Any] = Field(default_factory=dict, description="Source-specific extras.")
    provenance: Provenance | None = Field(default=None, description="Origin/audit record.")

    @field_validator(*_FLOAT_FIELDS, mode="after")
    @classmethod
    def _finite(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("must be a finite number (NaN/inf not allowed)")
        return value

    @property
    def has_sky_position(self) -> bool:
        """True if both RA and Dec are present."""
        return self.ra_deg is not None and self.dec_deg is not None

    @property
    def has_cartesian(self) -> bool:
        """True if all of x, y and z are present."""
        return self.x is not None and self.y is not None and self.z is not None

    @property
    def has_position(self) -> bool:
        """True if the object can be placed on the sky or in 3D space."""
        return self.has_sky_position or self.has_cartesian
