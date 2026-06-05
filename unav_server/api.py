"""FastAPI router: the local API endpoints, delegating to :class:`StateService`.

The router is thin — every endpoint maps a request onto a ``StateService`` call
and shapes the response. The service is resolved per-request from ``app.state``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from unav_core.data.schema import CatalogObject
from unav_core.db.importer import ImportSummary
from unav_core.missions import Mission
from unav_core.navigation import NavigatorState
from unav_core.navigation.bookmarks import Bookmark
from unav_core.routes import Route, RouteDistanceSummary
from unav_server.models import (
    DatasetSummary,
    HealthResponse,
    ImportJsonlRequest,
    MoveRequest,
    ObjectListResponse,
    RenderPayload,
    SkyRegionRequest,
    VisibleSectorRequest,
    VisibleSectorResponse,
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


@router.post("/navigator/move", response_model=NavigatorState)
def move_navigator(
    request: MoveRequest, service: StateService = Depends(get_service)
) -> NavigatorState:
    """Step the navigator one move in a camera-relative direction (persisted)."""
    try:
        return service.move(request.direction, request.distance)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/visible-sector/query", response_model=VisibleSectorResponse)
def visible_sector_query(
    request: VisibleSectorRequest, service: StateService = Depends(get_service)
) -> VisibleSectorResponse:
    """Lightweight visible-sector render objects (no metadata) for the viewports.

    Returns slim render objects (id/name, type/source, Cartesian + sky position,
    display colour/size); full metadata loads lazily via ``GET /objects/{uid}``.
    ``capped`` flags that the state's ``max_visible_objects`` limited the result.
    """
    effective_state = request.state or service.get_state()
    try:
        results = service.visible_sector(
            state=request.state,
            sort=request.sort,
            object_types=request.object_types,
            max_magnitude=request.max_magnitude,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    points = render_points(results)
    cap = effective_state.max_visible_objects
    return VisibleSectorResponse(
        count=len(points),
        capped=len(points) >= cap,
        max_visible_objects=cap,
        objects=points,
    )


@router.post("/visible-sector/query-current", response_model=VisibleSectorResponse)
def visible_sector_query_current(
    service: StateService = Depends(get_service),
) -> VisibleSectorResponse:
    """Lightweight visible-sector for the server's CURRENT persisted navigator state.

    The state-loop refresh action: query render objects from the authoritative
    navigator state (no body). Obeys the state's ``max_visible_objects`` and sets
    ``capped`` when the cap limited the result. Full metadata loads lazily via
    ``GET /objects/{uid}`` on selection. See ``docs/VISIBLE_SECTOR_REFRESH_MODEL.md``.
    """
    state = service.get_state()
    points = render_points(service.visible_sector_current())
    cap = state.max_visible_objects
    return VisibleSectorResponse(
        count=len(points),
        capped=len(points) >= cap,
        max_visible_objects=cap,
        objects=points,
    )


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


# --- bookmarks ---


@router.get("/bookmarks", response_model=list[Bookmark])
def list_bookmarks(service: StateService = Depends(get_service)) -> list[Bookmark]:
    return service.list_bookmarks()


@router.post("/bookmarks", response_model=Bookmark)
def create_bookmark(bookmark: Bookmark, service: StateService = Depends(get_service)) -> Bookmark:
    return service.add_bookmark(bookmark)


@router.delete("/bookmarks/{bookmark_id}", status_code=204)
def delete_bookmark_endpoint(
    bookmark_id: str, service: StateService = Depends(get_service)
) -> Response:
    if not service.delete_bookmark(bookmark_id):
        raise HTTPException(status_code=404, detail=f"bookmark {bookmark_id!r} not found")
    return Response(status_code=204)


# --- routes ---


@router.get("/routes", response_model=list[Route])
def list_routes(service: StateService = Depends(get_service)) -> list[Route]:
    return service.list_routes()


@router.post("/routes", response_model=Route)
def create_route(route: Route, service: StateService = Depends(get_service)) -> Route:
    return service.add_route(route)


@router.get("/routes/{route_id}", response_model=Route)
def get_route_endpoint(route_id: str, service: StateService = Depends(get_service)) -> Route:
    route = service.get_route(route_id)
    if route is None:
        raise HTTPException(status_code=404, detail=f"route {route_id!r} not found")
    return route


@router.put("/routes/{route_id}", response_model=Route)
def update_route_endpoint(
    route_id: str, route: Route, service: StateService = Depends(get_service)
) -> Route:
    return service.update_route(route_id, route)


@router.delete("/routes/{route_id}", status_code=204)
def delete_route_endpoint(route_id: str, service: StateService = Depends(get_service)) -> Response:
    if not service.delete_route(route_id):
        raise HTTPException(status_code=404, detail=f"route {route_id!r} not found")
    return Response(status_code=204)


@router.post("/routes/{route_id}/add-object/{uid}", response_model=Route)
def add_object_to_route_endpoint(
    route_id: str, uid: str, service: StateService = Depends(get_service)
) -> Route:
    try:
        return service.add_object_to_route(route_id, uid)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/routes/{route_id}/summary", response_model=RouteDistanceSummary)
def route_summary_endpoint(
    route_id: str, service: StateService = Depends(get_service)
) -> RouteDistanceSummary:
    route = service.get_route(route_id)
    if route is None:
        raise HTTPException(status_code=404, detail=f"route {route_id!r} not found")
    return route.distance_summary()


# --- missions ---


@router.get("/missions", response_model=list[Mission])
def list_missions(service: StateService = Depends(get_service)) -> list[Mission]:
    return service.list_missions()


@router.post("/missions", response_model=Mission)
def create_mission(mission: Mission, service: StateService = Depends(get_service)) -> Mission:
    return service.add_mission(mission)


@router.get("/missions/{mission_id}", response_model=Mission)
def get_mission_endpoint(mission_id: str, service: StateService = Depends(get_service)) -> Mission:
    mission = service.get_mission(mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail=f"mission {mission_id!r} not found")
    return mission


@router.put("/missions/{mission_id}", response_model=Mission)
def update_mission_endpoint(
    mission_id: str, mission: Mission, service: StateService = Depends(get_service)
) -> Mission:
    return service.update_mission(mission_id, mission)


@router.delete("/missions/{mission_id}", status_code=204)
def delete_mission_endpoint(
    mission_id: str, service: StateService = Depends(get_service)
) -> Response:
    if not service.delete_mission(mission_id):
        raise HTTPException(status_code=404, detail=f"mission {mission_id!r} not found")
    return Response(status_code=204)


@router.post("/missions/{mission_id}/add-route/{route_id}", response_model=Mission)
def add_route_to_mission_endpoint(
    mission_id: str, route_id: str, service: StateService = Depends(get_service)
) -> Mission:
    try:
        return service.add_route_to_mission(mission_id, route_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
