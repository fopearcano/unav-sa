"""Tests for the Astropy-backed time and epoch helpers."""

from datetime import datetime, timezone

import pytest

from unav_core.astro import time as t


def test_iso_to_julian_date_j2000() -> None:
    # 2000-01-01T12:00:00 UTC is JD 2451545.0.
    assert t.iso_to_julian_date("2000-01-01T12:00:00") == pytest.approx(2451545.0, abs=1e-6)


def test_julian_date_to_iso() -> None:
    assert t.julian_date_to_iso(2451545.0).startswith("2000-01-01T12:00:00")


def test_jd_iso_roundtrip() -> None:
    jd = 2459580.25
    assert t.iso_to_julian_date(t.julian_date_to_iso(jd)) == pytest.approx(jd, abs=1e-6)


def test_parse_time_accepts_datetime() -> None:
    dt = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    via_dt = t.iso_to_julian_date(dt)
    via_str = t.iso_to_julian_date("2020-01-01T00:00:00")
    assert via_dt == pytest.approx(via_str, abs=1e-6)


def test_parse_time_passthrough() -> None:
    now = t.current_time_utc()
    assert t.parse_time(now) is now


def test_parse_time_rejects_unsupported() -> None:
    with pytest.raises(TypeError):
        t.parse_time(12345)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        t.parse_time("")


def test_current_time_utc_scale() -> None:
    now = t.current_time_utc()
    assert now.scale == "utc"
    assert float(now.jd) > 2451545.0


@pytest.mark.parametrize(
    "value,expected",
    [
        (2016.0, "J2016.000"),
        ("J2000.0", "J2000.000"),
        ("2016", "J2016.000"),
        ("B1950", "B1950.000"),
    ],
)
def test_normalize_epoch(value: object, expected: str) -> None:
    assert t.normalize_epoch(value) == expected  # type: ignore[arg-type]


def test_normalize_epoch_errors() -> None:
    with pytest.raises(ValueError):
        t.normalize_epoch("")
    with pytest.raises(ValueError):
        t.normalize_epoch("not-a-year")
    with pytest.raises(TypeError):
        t.normalize_epoch(object())  # type: ignore[arg-type]
