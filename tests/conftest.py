"""Shared fixtures for the local API tests (FastAPI TestClient over in-memory DB)."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from unav_core.data import CatalogObject, ObjectType
from unav_core.db import import_objects
from unav_server.app import create_app


def _seed_objects() -> list[CatalogObject]:
    return [
        CatalogObject(
            uid="gaia:1",
            source="Gaia DR3",
            object_type=ObjectType.STAR,
            name="Vega",
            ra_deg=279.2,
            dec_deg=38.8,
            x=0.0,
            y=0.0,
            z=-10.0,
            apparent_magnitude=0.03,
        ),
        CatalogObject(
            uid="gaia:2",
            source="Gaia DR3",
            object_type=ObjectType.STAR,
            name="Sirius",
            x=5.0,
            y=0.0,
            z=-10.0,
            apparent_magnitude=-1.46,
        ),
        CatalogObject(
            uid="m87",
            source="NED",
            object_type=ObjectType.GALAXY,
            name="Virgo A",
            x=0.0,
            y=0.0,
            z=80.0,
            redshift=0.0043,
        ),
        CatalogObject(
            uid="3c273",
            source="SDSS",
            object_type=ObjectType.QUASAR,
            name="3C 273",
            x=0.0,
            y=0.0,
            z=10.0,
            redshift=0.158,
        ),
        # No Cartesian position (sky-only) -> used to test focus on an unplaceable object.
        CatalogObject(
            uid="nopos", source="s", object_type=ObjectType.STAR, ra_deg=1.0, dec_deg=2.0
        ),
    ]


@pytest.fixture
def empty_client() -> Iterator[TestClient]:
    app = create_app(":memory:")
    with TestClient(app) as client:
        yield client


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app(":memory:")
    import_objects(app.state.service.db, _seed_objects(), dataset_name="seed")
    with TestClient(app) as client:
        yield client
