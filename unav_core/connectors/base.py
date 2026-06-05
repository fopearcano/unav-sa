"""Shared connector infrastructure: lazy astroquery guard, errors and safety limits.

Connectors fetch *regional, limited* data from real archives and normalise it into
UNAV :class:`~unav_core.data.schema.CatalogObject` records. astroquery is an
**optional** dependency, imported lazily: importing a connector module never
requires astroquery, and a missing install raises
:class:`AstroqueryNotInstalledError` with an actionable message rather than
failing obscurely.

See ``docs/DATA_FETCHING_SAFETY.md``.
"""

from __future__ import annotations

import importlib
import math
import warnings
from collections.abc import Iterable
from types import ModuleType
from typing import Any

#: Default Gaia row cap (task safety default).
DEFAULT_GAIA_LIMIT = 500

#: Above this row count, callers get a loud warning ("no huge downloads").
HARD_WARN_LIMIT = 5000

#: Cone radius (deg) above which a query is refused unless explicitly allowed.
DEFAULT_MAX_RADIUS_DEG = 5.0

#: 1 astronomical unit in parsecs (IAU-defined factor); used for AU -> pc.
AU_IN_PC = 4.84813681e-6

_INSTALL_HINT = (
    "astroquery is required to fetch real data but is not installed.\n"
    "It is an OPTIONAL dependency of UNAV-SA (it must never be required inside a "
    "DCC plugin runtime).\n"
    "Install it with:\n"
    "    pip install astroquery\n"
    'or install the project query extra:\n    pip install -e ".[query]"'
)


class ConnectorError(RuntimeError):
    """Base class for all connector failures."""


class AstroqueryNotInstalledError(ConnectorError, ImportError):
    """Raised when a connector needs astroquery but it is not installed."""


class ConnectorNetworkError(ConnectorError):
    """Raised when the remote archive query fails (network/service error)."""


class EmptyResultError(ConnectorError):
    """Raised when a query succeeds but returns no rows."""


class MalformedResponseError(ConnectorError):
    """Raised when a response cannot be read or normalised into the schema."""


def astroquery_available() -> bool:
    """Return ``True`` if astroquery can be imported, ``False`` otherwise."""
    try:
        importlib.import_module("astroquery")
    except ImportError:
        return False
    return True


def require_astroquery(module_name: str) -> ModuleType:
    """Import an astroquery submodule, or raise :class:`AstroqueryNotInstalledError`."""
    try:
        return importlib.import_module(module_name)
    except ImportError as exc:
        raise AstroqueryNotInstalledError(_INSTALL_HINT) from exc


def enforce_limit(limit: int, *, hard_warn: int = HARD_WARN_LIMIT) -> int:
    """Validate a row limit; warn loudly above ``hard_warn`` (no huge downloads)."""
    if limit <= 0:
        raise ValueError("limit must be > 0")
    if limit > hard_warn:
        warnings.warn(
            f"requested limit {limit} exceeds the safe ceiling of {hard_warn}; "
            "UNAV-SA is designed for regional, limited fetches — large downloads "
            "are discouraged",
            stacklevel=3,
        )
    return limit


def enforce_radius(
    radius_deg: float,
    *,
    max_radius_deg: float = DEFAULT_MAX_RADIUS_DEG,
    allow_large: bool = False,
) -> float:
    """Validate a cone radius; refuse a huge radius unless explicitly allowed."""
    if radius_deg <= 0:
        raise ValueError("radius_deg must be > 0")
    if radius_deg > max_radius_deg and not allow_large:
        raise ValueError(
            f"radius {radius_deg} deg exceeds the safe cap of {max_radius_deg} deg; "
            "pass allow_large_radius=True to override (discouraged)"
        )
    return radius_deg


def to_float(value: Any) -> float | None:
    """Coerce a value to a finite float, or ``None`` (handles NaN/masked/missing)."""
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def extract_rows(results: Any) -> list[dict[str, Any]]:
    """Convert an astropy ``Table`` (or a sequence of mappings) to plain dict rows.

    Masked/NaN cells become ``None``. Raises :class:`MalformedResponseError` for
    anything that is not a readable table/row sequence.
    """
    if results is None:
        raise MalformedResponseError("connector received no result object")

    colnames = getattr(results, "colnames", None)
    if colnames is not None:
        try:
            return [{name: _scalarize(row[name]) for name in colnames} for row in results]
        except Exception as exc:  # noqa: BLE001 - surface any table-read failure clearly
            raise MalformedResponseError(f"could not read result table: {exc}") from exc

    if isinstance(results, Iterable) and not isinstance(results, (str, bytes, dict)):
        try:
            return [dict(row) for row in results]
        except (TypeError, ValueError) as exc:
            raise MalformedResponseError(f"unexpected result rows: {exc}") from exc

    raise MalformedResponseError(f"unexpected result type: {type(results).__name__}")


def _scalarize(value: Any) -> Any:
    import numpy as np

    if value is None:
        return None
    if value is np.ma.masked or np.ma.is_masked(value):
        return None
    if hasattr(value, "item"):
        try:
            value = value.item()
        except (ValueError, AttributeError):
            pass
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value
