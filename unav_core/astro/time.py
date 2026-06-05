"""Time and epoch helpers, backed by :class:`astropy.time.Time`.

Astropy handles calendar/JD conversions and time scales (UTC/TT/TDB) correctly,
so UNAV-SA never hand-rolls them. Naive :class:`datetime.datetime` values and
bare ISO strings are treated as UTC.

Requires Astropy — see :mod:`unav_core.astro._backend`.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import TYPE_CHECKING

from unav_core.astro._backend import get_time

if TYPE_CHECKING:
    from astropy.time import Time


def parse_time(value: str | datetime | Time) -> Time:
    """Parse a value into an Astropy :class:`~astropy.time.Time` (UTC scale).

    Accepts an ISO-8601 string, a :class:`datetime.datetime`, or an existing
    :class:`~astropy.time.Time` (returned unchanged). Naive datetimes and bare
    strings are interpreted as UTC.
    """
    time_mod = get_time()
    time_cls = time_mod.Time
    if isinstance(value, time_cls):
        return value
    if isinstance(value, datetime):
        return time_cls(value, scale="utc")
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError("empty time string")
        return time_cls(text, scale="utc")
    raise TypeError(
        f"unsupported time value of type {type(value).__name__!r}; "
        "expected an ISO-8601 string, datetime, or astropy Time"
    )


def iso_to_julian_date(value: str | datetime | Time) -> float:
    """Return the Julian Date (JD) of an ISO-8601 string (or datetime/Time)."""
    return float(parse_time(value).jd)


def julian_date_to_iso(jd: float) -> str:
    """Return the ISO-8601 (``isot``) representation of a Julian Date."""
    time_mod = get_time()
    return str(time_mod.Time(float(jd), format="jd", scale="utc").isot)


def current_time_utc() -> Time:
    """Return the current instant as an Astropy :class:`~astropy.time.Time` (UTC)."""
    return get_time().Time.now()


def normalize_epoch(value: str | float | Time) -> str:
    """Normalise an epoch to a canonical ``"J<year>"`` / ``"B<year>"`` string.

    Examples: ``2016.0 -> "J2016.000"``, ``"J2000.0" -> "J2000.000"``,
    ``"2016" -> "J2016.000"``, ``"B1950" -> "B1950.000"``. A bare number or a
    number with a ``J`` prefix is treated as a Julian epoch; a ``B`` prefix is a
    Besselian epoch. The value is validated via Astropy.
    """
    time_mod = get_time()
    time_cls = time_mod.Time

    if isinstance(value, time_cls):
        return f"J{value.jyear:.3f}"
    if isinstance(value, (int, float)):
        if not math.isfinite(value):
            raise ValueError("epoch must be a finite number")
        time_cls(float(value), format="jyear", scale="tt")  # validate
        return f"J{float(value):.3f}"
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError("empty epoch string")
        system = "J"
        body = text
        if text[0] in "JjBb":
            system = text[0].upper()
            body = text[1:]
        year = float(body)  # raises ValueError on malformed input
        fmt = "byear" if system == "B" else "jyear"
        time_cls(year, format=fmt, scale="tt")  # validate
        return f"{system}{year:.3f}"
    raise TypeError(
        f"unsupported epoch value of type {type(value).__name__!r}; "
        "expected a number, an epoch string, or astropy Time"
    )
