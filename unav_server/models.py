"""Request/response models (DTOs) for the local API.

These wrap or compose the canonical ``unav_core`` models (``CatalogObject``,
``NavigatorState``, ``Route``, ``Mission``, ``ImportSummary``), which are reused
directly as request/response bodies elsewhere in the API.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from unav_core.data.schema import CatalogObject
from unav_core.navigation.state import NavigatorState


class HealthResponse(BaseModel):
    """Liveness/info payload for ``GET /health``."""

    status: str
    object_count: int


class DatasetSummary(BaseModel):
    """One row of the local database's ``datasets`` table."""

    dataset_id: str
    name: str
    source: str
    object_count: int
    created_at: str


class ImportJsonlRequest(BaseModel):
    """Body for ``POST /datasets/import-jsonl`` (a server-local file path)."""

    path: str
    dataset_name: str
    enrich: bool = False


class ObjectListResponse(BaseModel):
    """A counted list of catalog objects."""

    count: int
    objects: list[CatalogObject]


class VisibleSectorRequest(BaseModel):
    """Body for ``POST /visible-sector/query``.

    If ``state`` is omitted, the server's current navigator state is used.
    """

    state: NavigatorState | None = None
    sort: str = "distance"
    object_types: list[str] | None = None
    max_magnitude: float | None = None


class RenderPoint(BaseModel):
    """A lightweight 3D render point (no metadata/provenance) for the viewport."""

    uid: str
    source: str
    object_type: str
    x: float
    y: float
    z: float
    color: str
    size: float
    name: str | None = None


class RenderPayload(BaseModel):
    """A counted list of render points for the 3D viewport."""

    count: int
    points: list[RenderPoint]


class SkyRegionRequest(BaseModel):
    """Body for ``POST /sky/query-region`` — an RA/Dec box (degrees).

    ``ra_min > ra_max`` selects a box that wraps across the 0/360 seam.
    """

    ra_min: float = Field(ge=0.0, le=360.0)
    ra_max: float = Field(ge=0.0, le=360.0)
    dec_min: float = Field(ge=-90.0, le=90.0)
    dec_max: float = Field(ge=-90.0, le=90.0)
    limit: int | None = Field(default=2000, ge=1, le=20000)

    @model_validator(mode="after")
    def _dec_order(self) -> SkyRegionRequest:
        if self.dec_max < self.dec_min:
            raise ValueError("dec_max must be >= dec_min")
        return self
