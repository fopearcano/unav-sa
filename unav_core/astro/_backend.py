"""Lazy Astropy import guard for the :mod:`unav_core.astro` layer.

Astropy is a *core* dependency of UNAV-SA's standalone engine (see
``docs/UNAV_SA_ARCHITECTURE.md``), but it is deliberately imported **lazily**:
importing :mod:`unav_core.astro` (or any of its submodules) performs no heavy
imports and no I/O. Astropy is only pulled in when a function that actually needs
it is called.

If Astropy is missing, the accessors here raise :class:`AstropyNotInstalledError`
with an actionable message rather than letting callers silently fall back to
hand-rolled (and likely incorrect) astronomy.
"""

from __future__ import annotations

import importlib
from types import ModuleType

_INSTALL_HINT = (
    "Astropy is required for UNAV-SA's astronomy layer (unav_core.astro) but is "
    "not installed.\n"
    "Astropy is a core dependency of the standalone engine; it must NOT be "
    "required inside a DCC plugin runtime.\n"
    "Install it with:\n"
    "    pip install astropy\n"
    "or install the project with its core dependencies:\n"
    "    pip install -e ."
)


class AstropyNotInstalledError(ImportError):
    """Raised when an Astropy-backed feature is used but Astropy is unavailable."""


def astropy_available() -> bool:
    """Return ``True`` if Astropy can be imported, ``False`` otherwise."""
    try:
        importlib.import_module("astropy")
    except ImportError:
        return False
    return True


def require_astropy() -> None:
    """Raise :class:`AstropyNotInstalledError` if Astropy cannot be imported."""
    _import_or_raise("astropy")


def _import_or_raise(module_name: str) -> ModuleType:
    try:
        return importlib.import_module(module_name)
    except ImportError as exc:  # noqa: B904 - message is the point; chain preserved below
        raise AstropyNotInstalledError(_INSTALL_HINT) from exc


def get_units() -> ModuleType:
    """Return the :mod:`astropy.units` module (or raise a helpful error)."""
    return _import_or_raise("astropy.units")


def get_coordinates() -> ModuleType:
    """Return the :mod:`astropy.coordinates` module (or raise a helpful error)."""
    return _import_or_raise("astropy.coordinates")


def get_time() -> ModuleType:
    """Return the :mod:`astropy.time` module (or raise a helpful error)."""
    return _import_or_raise("astropy.time")
