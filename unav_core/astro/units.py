"""Unit conversion helpers, backed by Astropy's IAU-defined unit system.

These wrap :mod:`astropy.units` so conversions use authoritative constants
rather than hand-coded factors. Inputs and outputs are plain numbers in the
named units (the canonical schema stores plain floats); the conversion itself is
performed by Astropy.

Requires Astropy — see :mod:`unav_core.astro._backend`.
"""

from __future__ import annotations

from unav_core.astro._backend import get_units


def _convert(value: float, src: str, dst: str) -> float:
    u = get_units()
    return float((value * getattr(u, src)).to_value(getattr(u, dst)))


def pc_to_ly(value: float) -> float:
    """Convert parsecs to light-years."""
    return _convert(value, "pc", "lyr")


def ly_to_pc(value: float) -> float:
    """Convert light-years to parsecs."""
    return _convert(value, "lyr", "pc")


def au_to_pc(value: float) -> float:
    """Convert astronomical units to parsecs."""
    return _convert(value, "au", "pc")


def pc_to_au(value: float) -> float:
    """Convert parsecs to astronomical units."""
    return _convert(value, "pc", "au")


def km_to_au(value: float) -> float:
    """Convert kilometres to astronomical units."""
    return _convert(value, "km", "au")


def au_to_km(value: float) -> float:
    """Convert astronomical units to kilometres."""
    return _convert(value, "au", "km")
