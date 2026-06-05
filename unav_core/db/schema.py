"""SQLite table definitions (SQLAlchemy Core) and row <-> object mapping.

Defines the local-cache schema:

* ``objects``    — the scalar ``CatalogObject`` fields + per-object provenance JSON;
* ``metadata``   — per-object metadata JSON (1:1 with ``objects``);
* ``datasets``   — descriptors of an import/query that produced objects;
* ``provenance`` — per-dataset provenance JSON;

plus the indexes that make filtering and spatial prefiltering fast.

The ``objects`` table stores every scalar field of ``CatalogObject`` (so the
inspector can show the full record, including provenance); ``metadata`` keeps the
free-form extras. See ``docs/LOCAL_DATABASE.md``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import Column, Float, Index, Integer, MetaData, String, Table, Text

from unav_core.data.object_types import ObjectType
from unav_core.data.schema import CatalogObject
from unav_core.provenance.provenance import Provenance

metadata_obj = MetaData()

objects_table = Table(
    "objects",
    metadata_obj,
    Column("uid", String, primary_key=True),
    Column("source", String, nullable=False),
    Column("object_type", String, nullable=False),
    Column("name", String),
    Column("ra_deg", Float),
    Column("dec_deg", Float),
    Column("distance_pc", Float),
    Column("parallax_mas", Float),
    Column("redshift", Float),
    Column("radial_velocity_kms", Float),
    Column("proper_motion_ra_masyr", Float),
    Column("proper_motion_dec_masyr", Float),
    Column("apparent_magnitude", Float),
    Column("absolute_magnitude", Float),
    Column("color_index", Float),
    Column("spectral_type", String),
    Column("x", Float),
    Column("y", Float),
    Column("z", Float),
    Column("provenance_json", Text),
)

metadata_table = Table(
    "metadata",
    metadata_obj,
    Column("uid", String, primary_key=True),
    Column("metadata_json", Text, nullable=False),
)

datasets_table = Table(
    "datasets",
    metadata_obj,
    Column("dataset_id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("source", String, nullable=False),
    Column("object_count", Integer, nullable=False, default=0),
    Column("created_at", String, nullable=False),
    Column("query_parameters_json", Text, nullable=False, default="{}"),
)

provenance_table = Table(
    "provenance",
    metadata_obj,
    Column("dataset_id", String, primary_key=True),
    Column("provenance_json", Text, nullable=False),
)

# --- voyage planning (bookmarks / routes / missions), persisted as JSON blobs ---
bookmarks_table = Table(
    "bookmarks",
    metadata_obj,
    Column("bookmark_id", String, primary_key=True),
    Column("created_at", String, nullable=False),
    Column("data_json", Text, nullable=False),
)

routes_table = Table(
    "routes",
    metadata_obj,
    Column("route_id", String, primary_key=True),
    Column("created_at", String, nullable=False),
    Column("data_json", Text, nullable=False),
)

missions_table = Table(
    "missions",
    metadata_obj,
    Column("mission_id", String, primary_key=True),
    Column("created_at", String, nullable=False),
    Column("data_json", Text, nullable=False),
)

# --- Indexes (task §4) ---
Index("ix_objects_source", objects_table.c.source)
Index("ix_objects_object_type", objects_table.c.object_type)
Index("ix_objects_ra_dec", objects_table.c.ra_deg, objects_table.c.dec_deg)
Index("ix_objects_x", objects_table.c.x)
Index("ix_objects_y", objects_table.c.y)
Index("ix_objects_z", objects_table.c.z)
Index("ix_objects_distance_pc", objects_table.c.distance_pc)
Index("ix_objects_redshift", objects_table.c.redshift)
Index("ix_objects_apparent_magnitude", objects_table.c.apparent_magnitude)


def object_core_values(obj: CatalogObject) -> dict[str, Any]:
    """Return the ``objects``-table column values for a ``CatalogObject``."""
    return {
        "uid": obj.uid,
        "source": obj.source,
        "object_type": obj.object_type.value,
        "name": obj.name,
        "ra_deg": obj.ra_deg,
        "dec_deg": obj.dec_deg,
        "distance_pc": obj.distance_pc,
        "parallax_mas": obj.parallax_mas,
        "redshift": obj.redshift,
        "radial_velocity_kms": obj.radial_velocity_kms,
        "proper_motion_ra_masyr": obj.proper_motion_ra_masyr,
        "proper_motion_dec_masyr": obj.proper_motion_dec_masyr,
        "apparent_magnitude": obj.apparent_magnitude,
        "absolute_magnitude": obj.absolute_magnitude,
        "color_index": obj.color_index,
        "spectral_type": obj.spectral_type,
        "x": obj.x,
        "y": obj.y,
        "z": obj.z,
        "provenance_json": obj.provenance.model_dump_json() if obj.provenance else None,
    }


def row_to_object(row: Mapping[str, Any], metadata: dict[str, Any] | None = None) -> CatalogObject:
    """Rebuild a ``CatalogObject`` from an ``objects`` row mapping (+ metadata).

    Every scalar field is rehydrated, including per-object provenance (parsed from
    ``provenance_json``). Free-form ``metadata`` is supplied separately.
    """
    provenance_json = row["provenance_json"] if "provenance_json" in row else None
    provenance = Provenance.model_validate_json(provenance_json) if provenance_json else None
    return CatalogObject(
        uid=row["uid"],
        source=row["source"],
        object_type=ObjectType.coerce(row["object_type"]),
        name=row["name"],
        ra_deg=row["ra_deg"],
        dec_deg=row["dec_deg"],
        distance_pc=row["distance_pc"],
        parallax_mas=row["parallax_mas"],
        redshift=row["redshift"],
        radial_velocity_kms=row["radial_velocity_kms"],
        proper_motion_ra_masyr=row["proper_motion_ra_masyr"],
        proper_motion_dec_masyr=row["proper_motion_dec_masyr"],
        apparent_magnitude=row["apparent_magnitude"],
        absolute_magnitude=row["absolute_magnitude"],
        color_index=row["color_index"],
        spectral_type=row["spectral_type"],
        x=row["x"],
        y=row["y"],
        z=row["z"],
        metadata=metadata or {},
        provenance=provenance,
    )
