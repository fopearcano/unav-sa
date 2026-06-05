"""Request/response models (DTOs) for the local API.

These wrap or compose the canonical ``unav_core`` models (``CatalogObject``,
``NavigatorState``, ``Route``, ``Mission``, ``ImportSummary``), which are reused
directly as request/response bodies elsewhere in the API.
"""

from __future__ import annotations

from pydantic import BaseModel

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
