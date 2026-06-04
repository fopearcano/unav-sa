"""Tests for the canonical data schema: CatalogObject, Dataset, ObjectType."""

import pytest
from pydantic import ValidationError

from unav_core.data import CANONICAL_UNITS, CatalogObject, Dataset, ObjectType
from unav_core.provenance import Provenance


def test_minimal_catalog_object() -> None:
    obj = CatalogObject(uid="x1", source="test", object_type=ObjectType.STAR)
    assert obj.uid == "x1"
    assert obj.object_type is ObjectType.STAR
    assert obj.name is None
    assert obj.metadata == {}
    assert obj.provenance is None
    assert obj.has_position is False


def test_object_type_coerce() -> None:
    assert ObjectType.coerce("GALAXY") is ObjectType.GALAXY
    assert ObjectType.coerce(" quasar ") is ObjectType.QUASAR
    assert ObjectType.coerce("flux-rope") is ObjectType.UNKNOWN
    assert ObjectType.coerce(None) is ObjectType.UNKNOWN
    assert ObjectType.coerce(ObjectType.MOON) is ObjectType.MOON


def test_object_type_serialises_to_lowercase_string() -> None:
    obj = CatalogObject(uid="x", source="s", object_type=ObjectType.NEBULA)
    assert obj.model_dump(mode="json")["object_type"] == "nebula"


def test_required_fields_enforced() -> None:
    with pytest.raises(ValidationError):
        CatalogObject(source="s", object_type=ObjectType.STAR)  # missing uid
    with pytest.raises(ValidationError):
        CatalogObject(uid="", source="s", object_type=ObjectType.STAR)  # empty uid


@pytest.mark.parametrize("ra", [-0.1, 360.0, 400.0])
def test_ra_out_of_range_rejected(ra: float) -> None:
    with pytest.raises(ValidationError):
        CatalogObject(uid="x", source="s", object_type=ObjectType.STAR, ra_deg=ra)


@pytest.mark.parametrize("dec", [-90.1, 90.1])
def test_dec_out_of_range_rejected(dec: float) -> None:
    with pytest.raises(ValidationError):
        CatalogObject(uid="x", source="s", object_type=ObjectType.STAR, dec_deg=dec)


def test_boundary_sky_position_accepted() -> None:
    obj = CatalogObject(uid="x", source="s", object_type=ObjectType.STAR, ra_deg=0.0, dec_deg=-90.0)
    assert obj.has_sky_position
    assert obj.has_position


def test_nan_and_inf_rejected() -> None:
    for bad in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValidationError):
            CatalogObject(uid="x", source="s", object_type=ObjectType.STAR, parallax_mas=bad)


def test_negative_parallax_allowed_structurally() -> None:
    # Real Gaia data contains negative parallaxes; the model must accept them.
    obj = CatalogObject(uid="x", source="s", object_type=ObjectType.STAR, parallax_mas=-0.5)
    assert obj.parallax_mas == -0.5


def test_extra_top_level_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        CatalogObject(uid="x", source="s", object_type=ObjectType.STAR, bogus=1)


def test_cartesian_position_helpers() -> None:
    obj = CatalogObject(uid="x", source="s", object_type=ObjectType.STAR, x=1.0, y=2.0, z=3.0)
    assert obj.has_cartesian
    assert obj.has_position
    assert not obj.has_sky_position


def test_roundtrip_model_dump_validate() -> None:
    prov = Provenance(source="Gaia", catalog="Gaia DR3", reference_frame="ICRS")
    obj = CatalogObject(
        uid="gaia-1",
        source="Gaia DR3",
        object_type=ObjectType.STAR,
        name="Vega",
        ra_deg=279.23,
        dec_deg=38.78,
        parallax_mas=130.23,
        apparent_magnitude=0.03,
        metadata={"band": "G"},
        provenance=prov,
    )
    restored = CatalogObject.model_validate(obj.model_dump(mode="json"))
    assert restored == obj
    assert restored.provenance is not None
    assert restored.provenance.source == "Gaia"


def test_canonical_units() -> None:
    assert CANONICAL_UNITS["ra_deg"] == "deg"
    assert CANONICAL_UNITS["distance_pc"] == "pc"
    assert CANONICAL_UNITS["x"] == "pc"
    assert CANONICAL_UNITS["radial_velocity_kms"] == "km/s"


def test_dataset_defaults_and_from_objects() -> None:
    objs = [
        CatalogObject(uid="a", source="s", object_type=ObjectType.STAR),
        CatalogObject(uid="b", source="s", object_type=ObjectType.GALAXY),
    ]
    ds = Dataset.from_objects(objs, dataset_id="d1", name="demo", source="s")
    assert ds.object_count == 2
    assert ds.coordinate_system == "ICRS"
    assert ds.units["ra_deg"] == "deg"
    assert ds.created_at.tzinfo is not None


def test_dataset_requires_non_empty_id() -> None:
    with pytest.raises(ValidationError):
        Dataset(dataset_id="", name="n", source="s")


def test_provenance_now_is_utc() -> None:
    prov = Provenance.now("SIMBAD")
    assert prov.source == "SIMBAD"
    assert prov.retrieved_at is not None
    assert prov.retrieved_at.tzinfo is not None
