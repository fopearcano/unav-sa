"""The :class:`Dataset` model: metadata describing a collection of objects."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from unav_core.data.schema import CANONICAL_UNITS, CatalogObject
from unav_core.provenance.provenance import Provenance


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Dataset(BaseModel):
    """Describes a named collection/result set of :class:`CatalogObject` records.

    A ``Dataset`` is *metadata about* a collection (e.g. a JSONL file or a query
    result) — not the container of the records themselves.
    """

    model_config = ConfigDict(extra="forbid")

    dataset_id: str = Field(min_length=1, description="Stable unique dataset id.")
    name: str = Field(min_length=1, description="Human-readable dataset name.")
    source: str = Field(min_length=1, description="Originating service/catalog.")
    description: str = Field(default="", description="Free-form description.")
    object_count: int = Field(default=0, ge=0, description="Number of objects in the collection.")
    created_at: datetime = Field(default_factory=_utcnow, description="UTC creation time.")
    query_parameters: dict[str, Any] = Field(
        default_factory=dict, description="Query parameters that produced the dataset."
    )
    coordinate_system: str = Field(default="ICRS", description="Reference frame of positions.")
    units: dict[str, str] = Field(
        default_factory=lambda: dict(CANONICAL_UNITS),
        description="Unit convention (field -> unit).",
    )
    provenance: Provenance | None = Field(default=None, description="Origin/audit record.")

    @classmethod
    def from_objects(
        cls,
        objects: Iterable[CatalogObject],
        *,
        dataset_id: str,
        name: str,
        source: str,
        **kwargs: Any,
    ) -> Dataset:
        """Build a dataset description from objects, filling ``object_count``."""
        materialised = list(objects)
        kwargs.setdefault("object_count", len(materialised))
        return cls(dataset_id=dataset_id, name=name, source=source, **kwargs)
