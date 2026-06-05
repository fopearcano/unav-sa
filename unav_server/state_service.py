"""StateService: the orchestration layer the API endpoints delegate to.

Holds the server's runtime state — the local :class:`~unav_core.db.database.Database`
handle, the current :class:`~unav_core.navigation.state.NavigatorState`, and an
in-memory store of routes/missions — and exposes plain methods over
``unav_core``. The API layer (FastAPI) stays a thin shell around this.

No astronomy logic lives here; it only composes core functions.
"""

from __future__ import annotations

from typing import Any

from unav_core.data.object_types import ObjectType
from unav_core.data.schema import CatalogObject
from unav_core.db import (
    Database,
    filter_by_source,
    filter_by_type,
    get_object,
    import_jsonl_to_db,
    objects_in_sky_box,
    search_by_name,
)
from unav_core.db.database import PathLike
from unav_core.db.importer import ImportSummary
from unav_core.missions import Mission
from unav_core.navigation import NavigatorState, visible_objects
from unav_core.routes import Route

_DEFAULT_SEARCH_LIMIT = 50


class StateService:
    """Runtime state and core orchestration for the local API server."""

    def __init__(self, db_path: PathLike = ":memory:") -> None:
        self.db = Database(db_path)
        self.state = NavigatorState()
        self._routes: dict[str, Route] = {}
        self._missions: dict[str, Mission] = {}

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

    # --- routes / missions (in-memory for this phase) ---

    def list_routes(self) -> list[Route]:
        return list(self._routes.values())

    def add_route(self, route: Route) -> Route:
        self._routes[route.route_id] = route
        return route

    def list_missions(self) -> list[Mission]:
        return list(self._missions.values())

    def add_mission(self, mission: Mission) -> Mission:
        self._missions[mission.mission_id] = mission
        return mission

    def dispose(self) -> None:
        self.db.dispose()
