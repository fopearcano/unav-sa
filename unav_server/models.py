"""Request/response models (DTOs) for the local API.

These wrap or compose the canonical ``unav_core`` models (``CatalogObject``,
``NavigatorState``, ``Route``, ``Mission``, ``ImportSummary``), which are reused
directly as request/response bodies elsewhere in the API.
"""

from __future__ import annotations

from typing import Literal

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


class MoveRequest(BaseModel):
    """Body for ``POST /navigator/move`` — a single camera-relative step.

    ``direction`` is relative to the navigator's current orientation; ``distance``
    is the step length in parsecs. Orientation (direction/up) is unchanged.
    """

    direction: Literal["forward", "back", "left", "right", "up", "down"]
    distance: float = Field(default=10.0, gt=0.0, description="Step length (parsecs).")


class RenderPoint(BaseModel):
    """A lightweight render object (no metadata/provenance) for the viewports.

    Carries only what a viewport (or a thin adapter) needs to draw and identify a
    point: identity, Cartesian + sky position, and presentation (display colour
    and size). Full records load lazily via ``GET /objects/{uid}`` on selection —
    metadata is never shipped per point. See ``docs/RENDER_PAYLOAD.md``.
    """

    uid: str
    name: str | None = None
    source: str
    object_type: str
    x: float
    y: float
    z: float
    ra_deg: float | None = None
    dec_deg: float | None = None
    distance_pc: float | None = None
    display_color: str
    display_size: float


class RenderPayload(BaseModel):
    """A counted list of render points (the adapter-facing render endpoints)."""

    count: int
    points: list[RenderPoint]


class VisibleSectorResponse(BaseModel):
    """Lightweight visible-sector result for the navigator viewports.

    ``objects`` are render objects (no metadata/provenance). ``capped`` is true
    when the result was limited by the state's ``max_visible_objects`` — more
    objects may be visible than were returned, and the UI warns when it is set.
    """

    count: int
    capped: bool
    max_visible_objects: int
    objects: list[RenderPoint]


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
