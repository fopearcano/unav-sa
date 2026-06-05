"""End-to-end coordinate pipeline: generation/enrichment -> DB -> spatial query.

Verifies that coordinate computation is centralised in ``unav_core.astro`` and
that the resulting Cartesian positions drive spatially meaningful visible-sector
queries — no hand-rolled astronomy anywhere downstream. See
``docs/COORDINATE_PIPELINE.md``.
"""

import pytest

from unav_core.astro.coordinates import radec_distance_to_cartesian
from unav_core.astro.enrich import enrich_object_coordinates
from unav_core.data import CatalogObject, ObjectType, generate_sample_catalog
from unav_core.db import Database, import_objects
from unav_core.navigation.state import NavigatorState
from unav_core.navigation.vector import Vec3
from unav_core.navigation.visible_sector import visible_objects


def _star(uid: str, ra: float, dec: float, distance_pc: float) -> CatalogObject:
    return CatalogObject(
        uid=uid,
        source="test",
        object_type=ObjectType.STAR,
        ra_deg=ra,
        dec_deg=dec,
        distance_pc=distance_pc,
    )


def test_sample_positions_are_astropy_backed() -> None:
    # Every enriched sample position matches the single central conversion.
    has_3d = 0
    for obj in generate_sample_catalog(100, seed=42):
        if obj.has_cartesian:
            expected = radec_distance_to_cartesian(obj.ra_deg, obj.dec_deg, obj.distance_pc)
            assert (obj.x, obj.y, obj.z) == pytest.approx(expected, abs=1e-9)
            has_3d += 1
    assert has_3d >= 50  # the catalog really contains usable 3D positions


def test_visible_sector_is_spatially_meaningful() -> None:
    # A near star toward +x and a far star toward -x (opposite side, out of range).
    near = enrich_object_coordinates(_star("near", 0.0, 0.0, 10.0))  # -> (10, 0, 0)
    far = enrich_object_coordinates(_star("far", 180.0, 0.0, 500.0))  # -> (-500, 0, 0)
    assert near.x == pytest.approx(10.0, abs=1e-9)
    assert far.x == pytest.approx(-500.0, abs=1e-9)

    db = Database(":memory:")
    try:
        import_objects(db, [near, far], dataset_name="t")
        # Camera at the origin looking toward +x, a narrow cone, far clip at 100 pc.
        state = NavigatorState(
            position=Vec3.of(0, 0, 0),
            direction=Vec3.of(1, 0, 0),
            up=Vec3.of(0, 1, 0),
            far_distance=100.0,
            cone_angle_degrees=10.0,
            max_visible_objects=100,
        )
        uids = {o.uid for o in visible_objects(db, state)}
        assert uids == {"near"}  # in range + inside the cone; far is behind & beyond
    finally:
        db.dispose()


def test_objects_without_cartesian_are_excluded() -> None:
    # A redshift-only galaxy cannot be placed in 3D, so it must not appear.
    galaxy = enrich_object_coordinates(
        CatalogObject(
            uid="g",
            source="test",
            object_type=ObjectType.GALAXY,
            ra_deg=0.0,
            dec_deg=0.0,
            redshift=0.1,
        )
    )
    assert not galaxy.has_cartesian

    db = Database(":memory:")
    try:
        import_objects(db, [galaxy], dataset_name="t")
        state = NavigatorState(
            position=Vec3.of(0, 0, 0), far_distance=100000.0, cone_angle_degrees=180.0
        )
        assert visible_objects(db, state) == []  # clearly excluded, never mis-placed
    finally:
        db.dispose()
