"""FastAPI router: the local API endpoints, delegating to :class:`StateService`.

The router is thin — every endpoint maps a request onto a ``StateService`` call
and shapes the response. The service is resolved per-request from ``app.state``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from unav_core.data.schema import CatalogObject
from unav_core.db.importer import ImportSummary
from unav_core.missions import Mission
from unav_core.navigation import NavigatorState
from unav_core.routes import Route
from unav_server.models import (
    DatasetSummary,
    HealthResponse,
    ImportJsonlRequest,
    ObjectListResponse,
    RenderPayload,
    SkyRegionRequest,
    VisibleSectorRequest,
)
from unav_server.render import render_points
from unav_server.state_service import StateService

router = APIRouter()


def get_service(request: Request) -> StateService:
    """Resolve the per-app :class:`StateService` from application state."""
    return request.app.state.service


@router.get("/health", response_model=HealthResponse)
def health(service: StateService = Depends(get_service)) -> HealthResponse:
    return HealthResponse(**service.health())


@router.get("/datasets", response_model=list[DatasetSummary])
def list_datasets(service: StateService = Depends(get_service)) -> list[DatasetSummary]:
    return [
        DatasetSummary(
            dataset_id=row["dataset_id"],
            name=row["name"],
            source=row["source"],
            object_count=row["object_count"],
            created_at=str(row["created_at"]),
        )
        for row in service.list_datasets()
    ]


@router.post("/datasets/import-jsonl", response_model=ImportSummary)
def import_jsonl(
    request: ImportJsonlRequest, service: StateService = Depends(get_service)
) -> ImportSummary:
    try:
        return service.import_jsonl(request.path, request.dataset_name, enrich=request.enrich)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/objects/search", response_model=ObjectListResponse)
def search_objects(
    q: str | None = Query(None, description="Name substring (case-insensitive)."),
    source: str | None = Query(None),
    object_type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=1000),
    service: StateService = Depends(get_service),
) -> ObjectListResponse:
    results = service.search(q=q, source=source, object_type=object_type, limit=limit)
    return ObjectListResponse(count=len(results), objects=results)


@router.get("/objects/{uid}", response_model=CatalogObject)
def get_object_endpoint(uid: str, service: StateService = Depends(get_service)) -> CatalogObject:
    obj = service.get_object(uid)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"object {uid!r} not found")
    return obj


@router.get("/navigator/state", response_model=NavigatorState)
def get_navigator_state(service: StateService = Depends(get_service)) -> NavigatorState:
    return service.get_state()


@router.post("/navigator/state", response_model=NavigatorState)
def set_navigator_state(
    state: NavigatorState, service: StateService = Depends(get_service)
) -> NavigatorState:
    return service.set_state(state)


@router.post("/navigator/focus/{uid}", response_model=NavigatorState)
def focus_object_endpoint(
    uid: str,
    distance: float | None = Query(None, gt=0.0),
    service: StateService = Depends(get_service),
) -> NavigatorState:
    try:
        return service.focus(uid, distance=distance)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"object {uid!r} not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/visible-sector/query", response_model=ObjectListResponse)
def visible_sector_query(
    request: VisibleSectorRequest, service: StateService = Depends(get_service)
) -> ObjectListResponse:
    try:
        results = service.visible_sector(
            state=request.state,
            sort=request.sort,
            object_types=request.object_types,
            max_magnitude=request.max_magnitude,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ObjectListResponse(count=len(results), objects=results)


@router.get("/visible-sector/current", response_model=ObjectListResponse)
def visible_sector_current(service: StateService = Depends(get_service)) -> ObjectListResponse:
    results = service.visible_sector_current()
    return ObjectListResponse(count=len(results), objects=results)


@router.post("/visible-sector/render", response_model=RenderPayload)
def visible_sector_render(
    request: VisibleSectorRequest, service: StateService = Depends(get_service)
) -> RenderPayload:
    """Lightweight 3D render payload (no metadata/provenance) for a navigator state."""
    try:
        objects = service.visible_sector(
            state=request.state,
            sort=request.sort,
            object_types=request.object_types,
            max_magnitude=request.max_magnitude,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    points = render_points(objects)
    return RenderPayload(count=len(points), points=points)


@router.get("/visible-sector/current/render", response_model=RenderPayload)
def visible_sector_current_render(
    service: StateService = Depends(get_service),
) -> RenderPayload:
    """Lightweight 3D render payload for the server's current navigator state."""
    points = render_points(service.visible_sector_current())
    return RenderPayload(count=len(points), points=points)


@router.post("/sky/query-region", response_model=ObjectListResponse)
def sky_query_region(
    request: SkyRegionRequest, service: StateService = Depends(get_service)
) -> ObjectListResponse:
    results = service.sky_region(
        ra_min=request.ra_min,
        ra_max=request.ra_max,
        dec_min=request.dec_min,
        dec_max=request.dec_max,
        limit=request.limit,
    )
    return ObjectListResponse(count=len(results), objects=results)


@router.get("/routes", response_model=list[Route])
def list_routes(service: StateService = Depends(get_service)) -> list[Route]:
    return service.list_routes()


@router.post("/routes", response_model=Route)
def create_route(route: Route, service: StateService = Depends(get_service)) -> Route:
    return service.add_route(route)


@router.get("/missions", response_model=list[Mission])
def list_missions(service: StateService = Depends(get_service)) -> list[Mission]:
    return service.list_missions()


@router.post("/missions", response_model=Mission)
def create_mission(mission: Mission, service: StateService = Depends(get_service)) -> Mission:
    return service.add_mission(mission)
