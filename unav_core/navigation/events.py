"""Navigation event model and a minimal synchronous event bus.

These typed events are the foundation for the App's reactivity and the future
server-side state sync (per ``docs/UNAV_SA_ARCHITECTURE.md``). The :class:`EventBus`
is a tiny in-process dispatcher; transport (WebSocket, etc.) is a later concern.

See ``docs/NAVIGATION_ENGINE.md``.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from unav_core.navigation.vector import Vec3


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class NavigationEventType(str, Enum):
    """The kinds of navigation events."""

    NAVIGATION_MOVED = "navigation_moved"
    VISIBLE_SECTOR_CHANGED = "visible_sector_changed"
    DATASET_CHANGED = "dataset_changed"
    OBJECT_SELECTED = "object_selected"
    ROUTE_CHANGED = "route_changed"


class NavigationEvent(BaseModel):
    """Base navigation event (carries its type and a UTC timestamp)."""

    model_config = ConfigDict(extra="forbid")

    type: NavigationEventType
    timestamp: datetime = Field(default_factory=_utcnow)


class NavigationMovedEvent(NavigationEvent):
    """The navigator's position/direction changed."""

    type: NavigationEventType = NavigationEventType.NAVIGATION_MOVED
    position: Vec3
    direction: Vec3


class VisibleSectorChangedEvent(NavigationEvent):
    """The set of visible objects changed."""

    type: NavigationEventType = NavigationEventType.VISIBLE_SECTOR_CHANGED
    visible_count: int
    object_uids: list[str] = Field(default_factory=list)


class DatasetChangedEvent(NavigationEvent):
    """The active dataset selection changed."""

    type: NavigationEventType = NavigationEventType.DATASET_CHANGED
    active_dataset_ids: list[str] = Field(default_factory=list)


class ObjectSelectedEvent(NavigationEvent):
    """An object was selected."""

    type: NavigationEventType = NavigationEventType.OBJECT_SELECTED
    uid: str


class RouteChangedEvent(NavigationEvent):
    """The active route changed."""

    type: NavigationEventType = NavigationEventType.ROUTE_CHANGED
    route_id: str | None = None
    waypoint_count: int = 0


EventHandler = Callable[[NavigationEvent], None]


class EventBus:
    """A minimal synchronous publish/subscribe dispatcher for navigation events."""

    def __init__(self) -> None:
        self._handlers: list[EventHandler] = []
        self._typed: dict[NavigationEventType, list[EventHandler]] = {}

    def subscribe(self, handler: EventHandler) -> EventHandler:
        """Subscribe to *all* events. Returns the handler (for later use)."""
        self._handlers.append(handler)
        return handler

    def subscribe_type(
        self, event_type: NavigationEventType, handler: EventHandler
    ) -> EventHandler:
        """Subscribe to a single event type."""
        self._typed.setdefault(event_type, []).append(handler)
        return handler

    def emit(self, event: NavigationEvent) -> None:
        """Dispatch ``event`` to all matching handlers (all-handlers first)."""
        for handler in list(self._handlers):
            handler(event)
        for handler in list(self._typed.get(event.type, [])):
            handler(event)

    def clear(self) -> None:
        self._handlers.clear()
        self._typed.clear()
