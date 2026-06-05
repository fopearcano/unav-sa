"""Bookmarks: saved objects or coordinates with a label, tags and notes.

Bookmarks are pure, serialisable data (no DB, no Astropy). A bookmark references
a catalog object (by ``uid``) and/or a Cartesian position (``Vec3``, parsecs).

See ``docs/BOOKMARKS.md``.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from unav_core.navigation.vector import Vec3

if TYPE_CHECKING:
    from unav_core.data.schema import CatalogObject


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex


def _object_position(obj: CatalogObject) -> Vec3 | None:
    x = getattr(obj, "x", None)
    y = getattr(obj, "y", None)
    z = getattr(obj, "z", None)
    if x is None or y is None or z is None:
        return None
    return Vec3(x=float(x), y=float(y), z=float(z))


class Bookmark(BaseModel):
    """A saved object and/or coordinate with a label, tags and notes."""

    model_config = ConfigDict(extra="forbid")

    bookmark_id: str = Field(default_factory=_new_id)
    label: str
    object_uid: str | None = None
    position: Vec3 | None = None
    tags: list[str] = Field(default_factory=list)
    notes: str = ""
    created_at: datetime = Field(default_factory=_utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _references_something(self) -> Bookmark:
        if self.object_uid is None and self.position is None:
            raise ValueError("a bookmark must reference an object_uid and/or a position")
        return self

    @classmethod
    def for_object(
        cls,
        obj: CatalogObject,
        *,
        label: str | None = None,
        tags: list[str] | None = None,
        notes: str = "",
    ) -> Bookmark:
        """Bookmark a catalog object (caches its Cartesian position if present)."""
        return cls(
            label=label or getattr(obj, "name", None) or obj.uid,
            object_uid=obj.uid,
            position=_object_position(obj),
            tags=list(tags or []),
            notes=notes,
        )

    @classmethod
    def for_coordinate(
        cls,
        position: Vec3,
        *,
        label: str,
        tags: list[str] | None = None,
        notes: str = "",
    ) -> Bookmark:
        """Bookmark a Cartesian coordinate (parsecs)."""
        return cls(label=label, position=position, tags=list(tags or []), notes=notes)

    def to_json(self, *, indent: int | None = 2) -> str:
        return self.model_dump_json(indent=indent)

    @classmethod
    def from_json(cls, text: str) -> Bookmark:
        return cls.model_validate_json(text)


class BookmarkCollection(BaseModel):
    """An ordered, serialisable collection of bookmarks."""

    model_config = ConfigDict(extra="forbid")

    bookmarks: list[Bookmark] = Field(default_factory=list)

    def add(self, bookmark: Bookmark) -> Bookmark:
        self.bookmarks.append(bookmark)
        return bookmark

    def remove(self, bookmark_id: str) -> Bookmark:
        for index, bookmark in enumerate(self.bookmarks):
            if bookmark.bookmark_id == bookmark_id:
                return self.bookmarks.pop(index)
        raise KeyError(bookmark_id)

    def get(self, bookmark_id: str) -> Bookmark | None:
        for bookmark in self.bookmarks:
            if bookmark.bookmark_id == bookmark_id:
                return bookmark
        return None

    def by_tag(self, tag: str) -> list[Bookmark]:
        return [bookmark for bookmark in self.bookmarks if tag in bookmark.tags]

    def __len__(self) -> int:
        return len(self.bookmarks)

    def to_json(self, *, indent: int | None = 2) -> str:
        return self.model_dump_json(indent=indent)

    @classmethod
    def from_json(cls, text: str) -> BookmarkCollection:
        return cls.model_validate_json(text)
