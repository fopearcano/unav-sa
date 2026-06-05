"""Tests for bookmarks and bookmark collections."""

import pytest
from pydantic import ValidationError

from unav_core.data import CatalogObject, ObjectType
from unav_core.navigation import Bookmark, BookmarkCollection, Vec3


def test_for_object_caches_position_and_label() -> None:
    star = CatalogObject(
        uid="gaia:1",
        source="Gaia DR3",
        object_type=ObjectType.STAR,
        name="Vega",
        x=1.0,
        y=2.0,
        z=3.0,
    )
    bm = Bookmark.for_object(star, tags=["fav"], notes="bright")
    assert bm.object_uid == "gaia:1"
    assert bm.label == "Vega"
    assert bm.position == Vec3.of(1.0, 2.0, 3.0)
    assert bm.tags == ["fav"]
    assert bm.notes == "bright"


def test_for_object_without_cartesian() -> None:
    obj = CatalogObject(uid="x", source="s", object_type=ObjectType.STAR, ra_deg=10.0, dec_deg=20.0)
    bm = Bookmark.for_object(obj)
    assert bm.object_uid == "x"
    assert bm.position is None  # still valid: references object_uid


def test_for_coordinate() -> None:
    bm = Bookmark.for_coordinate(Vec3.of(5, 0, 0), label="field", tags=["t"])
    assert bm.position == Vec3.of(5, 0, 0)
    assert bm.object_uid is None
    assert bm.label == "field"


def test_bookmark_must_reference_something() -> None:
    with pytest.raises(ValidationError):
        Bookmark(label="empty")  # neither object_uid nor position


def test_collection_add_get_remove() -> None:
    collection = BookmarkCollection()
    bm = collection.add(Bookmark.for_coordinate(Vec3.of(0, 0, 0), label="a"))
    assert len(collection) == 1
    assert collection.get(bm.bookmark_id) is bm
    assert collection.get("missing") is None
    removed = collection.remove(bm.bookmark_id)
    assert removed.bookmark_id == bm.bookmark_id
    assert len(collection) == 0
    with pytest.raises(KeyError):
        collection.remove("missing")


def test_collection_by_tag() -> None:
    collection = BookmarkCollection()
    collection.add(Bookmark.for_coordinate(Vec3.of(0, 0, 0), label="a", tags=["x", "y"]))
    collection.add(Bookmark.for_coordinate(Vec3.of(1, 0, 0), label="b", tags=["y"]))
    collection.add(Bookmark.for_coordinate(Vec3.of(2, 0, 0), label="c", tags=["z"]))
    assert {b.label for b in collection.by_tag("y")} == {"a", "b"}
    assert [b.label for b in collection.by_tag("z")] == ["c"]


def test_bookmark_json_roundtrip() -> None:
    bm = Bookmark.for_coordinate(Vec3.of(1, 2, 3), label="here", tags=["a"], notes="n")
    assert Bookmark.from_json(bm.to_json()) == bm


def test_collection_json_roundtrip() -> None:
    collection = BookmarkCollection()
    collection.add(Bookmark.for_coordinate(Vec3.of(0, 0, 0), label="a"))
    collection.add(Bookmark.for_coordinate(Vec3.of(1, 0, 0), label="b", tags=["t"]))
    assert BookmarkCollection.from_json(collection.to_json()) == collection
