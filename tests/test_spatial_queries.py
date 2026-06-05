"""Tests for cone (spatial) search and haversine angular separation."""

import random

import pytest

from unav_core.astro.coordinates import angular_separation as astropy_sep
from unav_core.data import CatalogObject, ObjectType
from unav_core.db import Database, angular_separation_deg, cone_search, import_objects


@pytest.mark.parametrize(
    "ra1,dec1,ra2,dec2",
    [
        (0.0, 0.0, 0.0, 90.0),
        (10.0, 20.0, 11.0, 21.0),
        (359.0, 0.0, 1.0, 0.0),
        (187.71, 12.39, 187.28, 2.05),
        (0.0, -90.0, 0.0, 90.0),
    ],
)
def test_haversine_matches_astropy(ra1: float, dec1: float, ra2: float, dec2: float) -> None:
    assert angular_separation_deg(ra1, dec1, ra2, dec2) == pytest.approx(
        astropy_sep(ra1, dec1, ra2, dec2), abs=1e-9
    )


def _make_db(objects: list[CatalogObject]) -> Database:
    db = Database(":memory:")
    import_objects(db, objects, dataset_name="t")
    return db


def test_cone_basic() -> None:
    db = _make_db(
        [
            CatalogObject(
                uid="center", source="t", object_type=ObjectType.STAR, ra_deg=100.0, dec_deg=0.0
            ),
            CatalogObject(
                uid="near", source="t", object_type=ObjectType.STAR, ra_deg=100.5, dec_deg=0.0
            ),
            CatalogObject(
                uid="far", source="t", object_type=ObjectType.STAR, ra_deg=120.0, dec_deg=0.0
            ),
        ]
    )
    assert {o.uid for o in cone_search(db, 100.0, 0.0, 1.0)} == {"center", "near"}
    db.dispose()


def test_cone_sorted_and_limited() -> None:
    db = _make_db(
        [
            CatalogObject(
                uid="d0", source="t", object_type=ObjectType.STAR, ra_deg=100.0, dec_deg=0.0
            ),
            CatalogObject(
                uid="d1", source="t", object_type=ObjectType.STAR, ra_deg=100.3, dec_deg=0.0
            ),
            CatalogObject(
                uid="d2", source="t", object_type=ObjectType.STAR, ra_deg=100.6, dec_deg=0.0
            ),
        ]
    )
    result = cone_search(db, 100.0, 0.0, 5.0, limit=2)
    assert [o.uid for o in result] == ["d0", "d1"]  # nearest first, limited
    db.dispose()


def _brute_force(objects: list[CatalogObject], ra: float, dec: float, radius: float) -> set[str]:
    return {
        o.uid
        for o in objects
        if angular_separation_deg(ra, dec, o.ra_deg, o.dec_deg) <= radius + 1e-9
    }


@pytest.mark.parametrize(
    "center,radius",
    [
        ((45.0, 10.0), 5.0),
        ((0.5, 0.0), 3.0),  # near the RA=0 seam
        ((359.0, -10.0), 4.0),  # near the RA=360 seam
        ((120.0, 88.0), 5.0),  # near the north pole
        ((200.0, -89.0), 6.0),  # near the south pole
        ((180.0, 0.0), 90.0),  # very large radius (a full hemisphere)
    ],
)
def test_cone_matches_brute_force(center: tuple[float, float], radius: float) -> None:
    rng = random.Random(1234)
    objects = [
        CatalogObject(
            uid=f"o{i}",
            source="t",
            object_type=ObjectType.STAR,
            ra_deg=rng.uniform(0.0, 359.999),
            dec_deg=rng.uniform(-89.9, 89.9),
        )
        for i in range(400)
    ]
    db = _make_db(objects)
    got = {o.uid for o in cone_search(db, center[0], center[1], radius)}
    expected = _brute_force(objects, center[0], center[1], radius)
    assert got == expected
    db.dispose()


def test_negative_radius_raises() -> None:
    db = Database(":memory:")
    with pytest.raises(ValueError):
        cone_search(db, 0.0, 0.0, -1.0)
    db.dispose()
