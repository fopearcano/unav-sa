"""Tests for the semantic / collection-level validation helpers."""

from typing import Any

from unav_core.data import CatalogObject, ObjectType
from unav_core.provenance import (
    Severity,
    detect_duplicate_uids,
    detect_invalid_parallax,
    detect_invalid_redshift,
    detect_malformed_metadata,
    detect_missing_coordinates,
    validate_object,
    validate_objects,
)


def _obj(**kwargs: Any) -> CatalogObject:
    base: dict[str, Any] = dict(uid="x", source="s", object_type=ObjectType.STAR)
    base.update(kwargs)
    return CatalogObject(**base)


def test_missing_coordinates_flagged() -> None:
    issue = detect_missing_coordinates(_obj())
    assert issue is not None
    assert issue.code == "missing_coordinates"
    assert issue.severity == Severity.ERROR


def test_missing_coordinates_ok_with_sky() -> None:
    assert detect_missing_coordinates(_obj(ra_deg=1.0, dec_deg=2.0)) is None


def test_missing_coordinates_ok_with_cartesian() -> None:
    assert detect_missing_coordinates(_obj(x=1.0, y=2.0, z=3.0)) is None


def test_invalid_parallax_is_a_warning() -> None:
    issue = detect_invalid_parallax(_obj(parallax_mas=-1.0))
    assert issue is not None
    assert issue.severity == Severity.WARNING
    assert detect_invalid_parallax(_obj(parallax_mas=0.0)) is not None
    assert detect_invalid_parallax(_obj(parallax_mas=5.0)) is None


def test_invalid_redshift_is_an_error() -> None:
    assert detect_invalid_redshift(_obj(redshift=-1.0)).severity == Severity.ERROR
    assert detect_invalid_redshift(_obj(redshift=-2.0)) is not None
    assert detect_invalid_redshift(_obj(redshift=-0.5)) is None  # blueshift is valid
    assert detect_invalid_redshift(_obj(redshift=3.0)) is None


def test_malformed_metadata_non_serialisable_value() -> None:
    issue = detect_malformed_metadata(_obj(metadata={"tags": {1, 2, 3}}))
    assert issue is not None
    assert issue.code == "malformed_metadata"


def test_malformed_metadata_nan_value() -> None:
    assert detect_malformed_metadata(_obj(metadata={"v": float("nan")})) is not None


def test_clean_metadata_ok() -> None:
    assert detect_malformed_metadata(_obj(metadata={"k": [1, 2, "x"], "n": 3})) is None


def test_duplicate_uid_detection() -> None:
    objs = [
        _obj(uid="dup", ra_deg=1.0, dec_deg=2.0),
        _obj(uid="dup", ra_deg=3.0, dec_deg=4.0),
        _obj(uid="solo", ra_deg=5.0, dec_deg=6.0),
    ]
    issues = detect_duplicate_uids(objs)
    assert len(issues) == 1
    assert issues[0].uid == "dup"
    assert issues[0].severity == Severity.ERROR


def test_duplicate_uid_detection_is_global_across_sources() -> None:
    # uid is the globally unique UNAV id: the same uid from different sources is a
    # collision (this is why source-native ids belong in native_id, not uid).
    objs = [
        _obj(uid="x:1", source="gaia", ra_deg=1.0, dec_deg=2.0),
        _obj(uid="x:1", source="sdss", ra_deg=3.0, dec_deg=4.0),
    ]
    issues = detect_duplicate_uids(objs)
    assert len(issues) == 1
    assert issues[0].uid == "x:1"
    assert issues[0].code == "duplicate_uid"


def test_validate_object_aggregates_issues() -> None:
    report = validate_object(_obj(parallax_mas=-1.0))  # missing coords + bad parallax
    codes = {issue.code for issue in report.issues}
    assert "missing_coordinates" in codes
    assert "invalid_parallax" in codes
    assert report.ok is False  # missing_coordinates is an ERROR


def test_warning_only_report_is_ok() -> None:
    # A non-positive parallax is only a WARNING, so with a valid position the
    # report should still be "ok".
    report = validate_object(_obj(ra_deg=1.0, dec_deg=2.0, parallax_mas=-0.3))
    assert report.warnings
    assert report.ok


def test_validate_objects_includes_duplicates() -> None:
    good = [
        _obj(uid="a", ra_deg=1.0, dec_deg=2.0, parallax_mas=5.0),
        _obj(uid="b", ra_deg=3.0, dec_deg=4.0),
    ]
    report = validate_objects(good)
    assert report.ok
    assert len(report) == 0

    dupes = [
        _obj(uid="a", ra_deg=1.0, dec_deg=2.0),
        _obj(uid="a", ra_deg=1.0, dec_deg=2.0),
    ]
    report2 = validate_objects(dupes)
    assert not report2.ok
    assert any(issue.code == "duplicate_uid" for issue in report2.issues)
