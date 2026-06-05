# UNAV-SA — Bookmarks

`unav_core.navigation.bookmarks` lets a user save objects or coordinates with a
label, tags and notes. Bookmarks are pure, serialisable data (no DB, no Astropy)
and integrate with routes (a waypoint can reference a bookmark).

> Phase 8 scope. Coordinates are Cartesian parsecs (`Vec3`), the same space as
> `CatalogObject.x/y/z`.

## Bookmark

| Field | Notes |
| --- | --- |
| `bookmark_id` | stable id (auto-generated) |
| `label` | human-readable label (required) |
| `object_uid` | saved catalog object's uid (optional) |
| `position` | saved Cartesian coordinate `Vec3` (optional) |
| `tags` | list of tags |
| `notes` | free-form text |
| `created_at` | UTC timestamp |
| `metadata` | extras |

A bookmark must reference **at least one** of `object_uid` / `position`
(validated).

```python
from unav_core.navigation import Bookmark, BookmarkCollection, Vec3

star_bm = Bookmark.for_object(some_star, tags=["favourite"], notes="naked-eye")
field_bm = Bookmark.for_coordinate(Vec3.of(10, 0, 0), label="Empty field")

collection = BookmarkCollection()
collection.add(star_bm)
collection.add(field_bm)
collection.by_tag("favourite")   # -> [star_bm]
```

`Bookmark.for_object` caches the object's Cartesian position (if present) so the
bookmark can be navigated to without a live DB.

## BookmarkCollection

`add(bookmark)`, `remove(bookmark_id)` (raises `KeyError` if missing),
`get(bookmark_id)`, `by_tag(tag)`, `len(collection)`.

## Use with routes

A bookmark becomes a waypoint via `Waypoint.from_bookmark(bookmark)` (kind
`bookmark`), carrying the bookmark's `object_uid`/`position` for analytics. See
[`ROUTES_AND_WAYPOINTS.md`](ROUTES_AND_WAYPOINTS.md).

## Serialization

`bookmark.to_json()` / `Bookmark.from_json(text)` and
`collection.to_json()` / `BookmarkCollection.from_json(text)` round-trip through
JSON.
