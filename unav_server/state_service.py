"""StateService: the orchestration layer the API endpoints delegate to.

Holds the server's runtime state — the local :class:`~unav_core.db.database.Database`
handle and the current :class:`~unav_core.navigation.state.NavigatorState` — and
exposes plain methods over ``unav_core``. Voyage plans (bookmarks, routes,
missions) are **persisted** in the same database (see
:mod:`unav_core.db.planning`), so they survive an app restart. The API layer
(FastAPI) stays a thin shell around this.

No astronomy logic lives here; it only composes core functions.
"""

from __future__ import annotations

from typing import Any

from unav_core.data.object_types import ObjectType
from unav_core.data.schema import CatalogObject
from unav_core.db import (
    Database,
    delete_bookmark,
    delete_mission,
    delete_route,
    filter_by_source,
    filter_by_type,
    get_mission,
    get_object,
    get_route,
    import_jsonl_to_db,
    list_bookmarks,
    list_missions,
    list_routes,
    objects_in_sky_box,
    save_bookmark,
    save_mission,
    save_route,
    search_by_name,
)
from unav_core.db.database import PathLike
from unav_core.db.importer import ImportSummary
from unav_core.missions import Mission, MissionSegment
from unav_core.navigation import NavigatorState, visible_objects
from unav_core.navigation.bookmarks import Bookmark
from unav_core.navigation.vector import Vec3
from unav_core.routes import Route, Waypoint

_DEFAULT_SEARCH_LIMIT = 50
_DEFAULT_TRANSITION_SECONDS = 10.0

#: Camera-relative move directions -> (Camera method, sign).
_MOVES: dict[str, tuple[str, float]] = {
    "forward": ("move_forward", 1.0),
    "back": ("move_forward", -1.0),
    "right": ("move_right", 1.0),
    "left": ("move_right", -1.0),
    "up": ("move_up", 1.0),
    "down": ("move_up", -1.0),
}


class StateService:
    """Runtime state and core orchestration for the local API server."""

    def __init__(self, db_path: PathLike = ":memory:") -> None:
        self.db = Database(db_path)
        self.state = NavigatorState()

    # --- health / datasets ---

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "object_count": self.db.count_objects()}

    def list_datasets(self) -> list[dict[str, Any]]:
        return self.db.list_datasets()

    def import_jsonl(
        self, path: PathLike, dataset_name: str, *, enrich: bool = False
    ) -> ImportSummary:
        return import_jsonl_to_db(
            path, self.db.db_path, dataset_name, enrich=enrich, database=self.db
        )

    # --- objects ---

    def search(
        self,
        *,
        q: str | None = None,
        source: str | None = None,
        object_type: str | None = None,
        limit: int = _DEFAULT_SEARCH_LIMIT,
    ) -> list[CatalogObject]:
        if q:
            results = search_by_name(self.db, q, limit=limit)
        elif source:
            results = filter_by_source(self.db, source, limit=limit)
        elif object_type:
            results = filter_by_type(self.db, object_type, limit=limit)
        else:
            results = self.db.fetch_objects(limit=limit)

        # Apply secondary filters in Python when more than one is given.
        if q and source:
            results = [obj for obj in results if obj.source == source]
        if (q or source) and object_type:
            target = ObjectType.coerce(object_type)
            results = [obj for obj in results if obj.object_type == target]
        return results

    def get_object(self, uid: str) -> CatalogObject | None:
        return get_object(self.db, uid)

    # --- navigator ---

    def get_state(self) -> NavigatorState:
        return self.state

    def set_state(self, state: NavigatorState) -> NavigatorState:
        self.state = state
        return self.state

    def focus(self, uid: str, *, distance: float | None = None) -> NavigatorState:
        obj = get_object(self.db, uid)
        if obj is None:
            raise KeyError(uid)
        if not obj.has_cartesian:
            raise ValueError(f"object {uid!r} has no Cartesian position to focus on")
        camera = self.state.to_camera()
        camera.focus_object(obj, distance=distance)
        params = self.state.model_dump(exclude={"position", "direction", "up"})
        self.state = NavigatorState.from_camera(camera, **params)
        return self.state

    def move(self, direction: str, distance: float) -> NavigatorState:
        """Step the navigator ``distance`` pc in a camera-relative ``direction``.

        Orientation and the viewing parameters (fov/clip/cone/cap/epoch) are
        preserved; only the position moves. The new state is persisted.
        """
        spec = _MOVES.get(direction)
        if spec is None:
            valid = ", ".join(_MOVES)
            raise ValueError(f"unknown direction {direction!r}; expected one of {valid}")
        method, sign = spec
        camera = self.state.to_camera()
        getattr(camera, method)(sign * distance)
        params = self.state.model_dump(exclude={"position", "direction", "up"})
        self.state = NavigatorState.from_camera(camera, **params)
        return self.state

    def visible_sector(
        self,
        *,
        state: NavigatorState | None = None,
        sort: str = "distance",
        object_types: list[str] | None = None,
        max_magnitude: float | None = None,
    ) -> list[CatalogObject]:
        target_state = state or self.state
        types = {ObjectType.coerce(t) for t in object_types} if object_types else None
        return visible_objects(
            self.db, target_state, sort=sort, object_types=types, max_magnitude=max_magnitude
        )

    def visible_sector_current(self) -> list[CatalogObject]:
        """The visible sector for the server's current navigator state."""
        return self.visible_sector()

    def sky_region(
        self,
        *,
        ra_min: float,
        ra_max: float,
        dec_min: float,
        dec_max: float,
        limit: int | None = None,
    ) -> list[CatalogObject]:
        """Objects within an RA/Dec box (for the 2D sky view)."""
        return objects_in_sky_box(self.db, ra_min, ra_max, dec_min, dec_max, limit=limit)

    # --- bookmarks (persisted) ---

    def list_bookmarks(self) -> list[Bookmark]:
        return list_bookmarks(self.db)

    def add_bookmark(self, bookmark: Bookmark) -> Bookmark:
        """Persist a bookmark; cache the object's position from the DB if missing."""
        if bookmark.object_uid and bookmark.position is None:
            obj = get_object(self.db, bookmark.object_uid)
            if obj is not None and obj.has_cartesian:
                bookmark = bookmark.model_copy(update={"position": Vec3(x=obj.x, y=obj.y, z=obj.z)})
        return save_bookmark(self.db, bookmark)

    def delete_bookmark(self, bookmark_id: str) -> bool:
        return delete_bookmark(self.db, bookmark_id)

    # --- routes (persisted) ---

    def list_routes(self) -> list[Route]:
        return list_routes(self.db)

    def get_route(self, route_id: str) -> Route | None:
        return get_route(self.db, route_id)

    def add_route(self, route: Route) -> Route:
        return save_route(self.db, route)

    def update_route(self, route_id: str, route: Route) -> Route:
        return save_route(self.db, route.model_copy(update={"route_id": route_id}))

    def delete_route(self, route_id: str) -> bool:
        return delete_route(self.db, route_id)

    def add_object_to_route(self, route_id: str, uid: str) -> Route:
        """Append a catalog object (by uid) as a waypoint and persist the route."""
        route = get_route(self.db, route_id)
        if route is None:
            raise LookupError(f"route {route_id!r} not found")
        obj = get_object(self.db, uid)
        if obj is None:
            raise LookupError(f"object {uid!r} not found")
        route.add_waypoint(Waypoint.from_object(obj))
        return save_route(self.db, route)

    # --- missions (persisted) ---

    def list_missions(self) -> list[Mission]:
        return list_missions(self.db)

    def get_mission(self, mission_id: str) -> Mission | None:
        return get_mission(self.db, mission_id)

    def add_mission(self, mission: Mission) -> Mission:
        return save_mission(self.db, mission)

    def update_mission(self, mission_id: str, mission: Mission) -> Mission:
        return save_mission(self.db, mission.model_copy(update={"mission_id": mission_id}))

    def delete_mission(self, mission_id: str) -> bool:
        return delete_mission(self.db, mission_id)

    def add_route_to_mission(self, mission_id: str, route_id: str) -> Mission:
        """Extend a mission with another route's waypoints (+ a segment each)."""
        mission = get_mission(self.db, mission_id)
        if mission is None:
            raise LookupError(f"mission {mission_id!r} not found")
        route = get_route(self.db, route_id)
        if route is None:
            raise LookupError(f"route {route_id!r} not found")
        existing = {w.wid for w in mission.route.waypoints}
        added = [w for w in route.waypoints if w.wid not in existing]
        mission.route.waypoints.extend(added)
        mission.segments.extend(
            MissionSegment(waypoint_id=w.wid, transition_seconds=_DEFAULT_TRANSITION_SECONDS)
            for w in added
        )
        return save_mission(self.db, mission)

    def dispose(self) -> None:
        self.db.dispose()
