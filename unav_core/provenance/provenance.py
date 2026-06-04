"""The :class:`Provenance` record: where a datum came from.

Provenance captures *enough* to reproduce and audit a result: which service,
which catalog/release and version, the exact query, when it was retrieved, and
the frame/epoch/unit assumptions in force. It is attached to records as they
enter the system and travels with them through cache, navigation and export.

See ``docs/PROVENANCE_AND_VALIDATION.md`` and ``docs/DATA_SOURCE_STRATEGY.md``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Provenance(BaseModel):
    """Origin and retrieval metadata attached to records and datasets."""

    model_config = ConfigDict(extra="forbid")

    source: str = Field(min_length=1, description="Originating service, e.g. 'Gaia'.")
    catalog: str | None = Field(default=None, description="Catalog/release, e.g. 'Gaia DR3'.")
    version: str | None = Field(default=None, description="Version identifier, if any.")
    reference_frame: str | None = Field(default=None, description="e.g. 'ICRS', 'Galactic'.")
    epoch: str | None = Field(default=None, description="Reference epoch, e.g. 'J2016.0'.")
    query_parameters: dict[str, Any] = Field(
        default_factory=dict, description="Exact query parameters."
    )
    units: dict[str, str] = Field(
        default_factory=dict, description="Unit assumptions (field -> unit)."
    )
    endpoint: str | None = Field(default=None, description="Service endpoint/URL used.")
    retrieved_at: datetime | None = Field(default=None, description="UTC retrieval timestamp.")
    notes: str | None = Field(default=None, description="Free-form notes.")

    @classmethod
    def now(cls, source: str, **kwargs: Any) -> Provenance:
        """Build a provenance record stamped with the current UTC time."""
        return cls(source=source, retrieved_at=datetime.now(timezone.utc), **kwargs)
