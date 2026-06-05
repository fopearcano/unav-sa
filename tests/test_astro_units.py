"""Tests for the Astropy-backed unit conversion helpers."""

import sys

import pytest

from unav_core.astro import _backend, units


def test_pc_to_ly_value() -> None:
    assert units.pc_to_ly(1.0) == pytest.approx(3.2615638, rel=1e-6)


def test_ly_pc_roundtrip() -> None:
    assert units.ly_to_pc(units.pc_to_ly(3.5)) == pytest.approx(3.5, rel=1e-12)


def test_au_pc_value_and_roundtrip() -> None:
    assert units.pc_to_au(1.0) == pytest.approx(206264.806, rel=1e-6)
    assert units.au_to_pc(units.pc_to_au(2.0)) == pytest.approx(2.0, rel=1e-12)


def test_km_au_value_and_roundtrip() -> None:
    # IAU definition: 1 au = 149,597,870.7 km exactly.
    assert units.au_to_km(1.0) == pytest.approx(149_597_870.7, rel=1e-9)
    assert units.km_to_au(149_597_870.7) == pytest.approx(1.0, rel=1e-12)


def test_missing_astropy_raises_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    # Block (re)importing astropy and any already-cached submodules.
    for name in list(sys.modules):
        if name == "astropy" or name.startswith("astropy."):
            monkeypatch.setitem(sys.modules, name, None)

    assert _backend.astropy_available() is False
    with pytest.raises(_backend.AstropyNotInstalledError) as excinfo:
        units.pc_to_ly(1.0)
    message = str(excinfo.value)
    assert "pip install astropy" in message
    assert "unav_core.astro" in message
