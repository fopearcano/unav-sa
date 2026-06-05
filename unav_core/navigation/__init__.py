"""Navigation state and the real-time navigator.

Owns the **navigation state**: the observer/camera pose, reference frame, field
of view, target selection, and the real-time update loop that the App and
adapters drive. Navigation is expressed in core astronomical terms (frames,
coordinates and distances from :mod:`unav_core.astro`) and is fully decoupled
from any renderer or DCC.

Pieces:

* :class:`~unav_core.navigation.vector.Vec3` — tiny pure-Python 3D vector;
* :class:`~unav_core.navigation.camera.Camera` — live pose controller;
* :class:`~unav_core.navigation.state.NavigatorState` — serialisable state;
* the event model + :class:`~unav_core.navigation.events.EventBus`;
* :func:`~unav_core.navigation.visible_sector.visible_objects` — visible-sector query.

The pose/state/event pieces are intentionally dependency-light (no SQLAlchemy,
no Astropy), so an adapter can consume a ``NavigatorState`` without the database
stack. ``visible_objects`` needs the local cache, so it is imported lazily.
"""

from typing import TYPE_CHECKING

from unav_core.navigation.camera import Camera
from unav_core.navigation.events import (
    DatasetChangedEvent,
    EventBus,
    NavigationEvent,
    NavigationEventType,
    NavigationMovedEvent,
    ObjectSelectedEvent,
    RouteChangedEvent,
    VisibleSectorChangedEvent,
)
from unav_core.navigation.state import NavigatorState
from unav_core.navigation.vector import Vec3

if TYPE_CHECKING:
    from unav_core.navigation.visible_sector import visible_objects

__all__ = [
    "Vec3",
    "Camera",
    "NavigatorState",
    "visible_objects",
    "EventBus",
    "NavigationEvent",
    "NavigationEventType",
    "NavigationMovedEvent",
    "VisibleSectorChangedEvent",
    "DatasetChangedEvent",
    "ObjectSelectedEvent",
    "RouteChangedEvent",
]


def __getattr__(name: str) -> object:
    # Lazily expose the DB-backed query so importing the pose/state/event pieces
    # never pulls in the database stack (keeps adapters light).
    if name == "visible_objects":
        from unav_core.navigation.visible_sector import visible_objects

        return visible_objects
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
