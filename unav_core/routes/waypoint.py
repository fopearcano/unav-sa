"""Waypoints: the typed stops that make up a route.

A waypoint references a target by ``uid`` and/or caches a Cartesian position
(``Vec3``, parsecs) for planning/analytics. Waypoints are pure data — they do not
hold DB connections; a catalog-object waypoint stores the object's ``uid`` and a
cached position rather than the live record.

See ``docs/ROUTES_AND_WAYPOINTS.md``.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from unav_core.data.object_types import ObjectType
from unav_core.navigation.vector import Vec3

if TYPE_CHECKING:
    from unav_core.data.schema import CatalogObject
    from unav_core.navigation.bookmarks import Bookmark


def _new_id() -> str:
    return uuid.uuid4().hex


def _object_position(obj: CatalogObject) -> Vec3 | None:
    x = getattr(obj, "x", None)
    y = getattr(obj, "y", None)
    z = getattr(obj, "z", None)
    if x is None or y is None or z is None:
        return None
    return Vec3(x=float(x), y=float(y), z=float(z))


class WaypointKind(str, Enum):
    """What a waypoint represents."""

    CATALOG_OBJECT = "catalog_object"
    COORDINATE = "coordinate"
    BOOKMARK = "bookmark"
    ANNOTATION_ONLY = "annotation_only"
    CUSTOM = "custom"


class Waypoint(BaseModel):
    """One stop in a route. The required fields depend on ``kind``."""

    model_config = ConfigDict(extra="forbid")

    wid: str = Field(default_factory=_new_id)
    kind: WaypointKind
    label: str | None = None
    object_uid: str | None = None
    bookmark_id: str | None = None
    position: Vec3 | None = None
    object_type: ObjectType | None = None
    source: str | None = None
    annotation: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_kind(self) -> Waypoint:
        if self.kind is WaypointKind.CATALOG_OBJECT and not self.object_uid:
            raise ValueError("a catalog_object waypoint requires object_uid")
        if self.kind is WaypointKind.COORDINATE and self.position is None:
            raise ValueError("a coordinate waypoint requires a position")
        if self.kind is WaypointKind.BOOKMARK and not self.bookmark_id:
            raise ValueError("a bookmark waypoint requires bookmark_id")
        if self.kind is WaypointKind.ANNOTATION_ONLY and not (self.annotation or self.label):
            raise ValueError("an annotation_only waypoint requires annotation or label")
        return self

    @property
    def has_position(self) -> bool:
        return self.position is not None

    @classmethod
    def from_object(
        cls, obj: CatalogObject, *, label: str | None = None, metadata: dict[str, Any] | None = None
    ) -> Waypoint:
        """A ``catalog_object`` waypoint (caches uid, type, source and position)."""
        return cls(
            kind=WaypointKind.CATALOG_OBJECT,
            object_uid=obj.uid,
            label=label or getattr(obj, "name", None) or obj.uid,
            position=_object_position(obj),
            object_type=obj.object_type,
            source=obj.source,
            metadata=dict(metadata or {}),
        )

    @classmethod
    def from_coordinate(
        cls, position: Vec3, *, label: str | None = None, metadata: dict[str, Any] | None = None
    ) -> Waypoint:
        """A ``coordinate`` waypoint at a Cartesian position (parsecs)."""
        return cls(
            kind=WaypointKind.COORDINATE,
            position=position,
            label=label,
            metadata=dict(metadata or {}),
        )

    @classmethod
    def from_bookmark(cls, bookmark: Bookmark, *, label: str | None = None) -> Waypoint:
        """A ``bookmark`` waypoint referencing an existing bookmark."""
        return cls(
            kind=WaypointKind.BOOKMARK,
            bookmark_id=bookmark.bookmark_id,
            object_uid=bookmark.object_uid,
            position=bookmark.position,
            label=label or bookmark.label,
        )

    @classmethod
    def annotation_waypoint(
        cls,
        text: str,
        *,
        label: str | None = None,
        position: Vec3 | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Waypoint:
        """An ``annotation_only`` waypoint (a note; no travel stop required)."""
        return cls(
            kind=WaypointKind.ANNOTATION_ONLY,
            annotation=text,
            label=label,
            position=position,
            metadata=dict(metadata or {}),
        )

    @classmethod
    def custom(
        cls,
        *,
        label: str | None = None,
        position: Vec3 | None = None,
        object_uid: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Waypoint:
        """A ``custom`` waypoint with caller-defined contents."""
        return cls(
            kind=WaypointKind.CUSTOM,
            label=label,
            position=position,
            object_uid=object_uid,
            metadata=dict(metadata or {}),
        )
