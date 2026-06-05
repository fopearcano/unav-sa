"""Reference-frame registry for the astronomy layer.

UNAV-SA works in **ICRS** by default (matching the canonical schema, whose
``ra_deg``/``dec_deg`` are ICRS). This module maps short, stable frame names to
Astropy frame classes so other layers can request a frame by name without
importing Astropy themselves.

Requires Astropy only when a concrete frame is requested via :func:`get_frame`.
See :mod:`unav_core.astro._backend`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from unav_core.astro._backend import get_coordinates

if TYPE_CHECKING:
    from astropy.coordinates import BaseCoordinateFrame

#: Short, canonical names of the frames UNAV-SA understands.
SUPPORTED_FRAMES: tuple[str, ...] = ("icrs", "galactic", "fk5", "fk4")

#: The default working frame for the canonical schema.
DEFAULT_FRAME = "icrs"


def normalize_frame_name(name: str) -> str:
    """Return the canonical (lower-case) frame name, or raise ``ValueError``."""
    key = name.strip().lower()
    if key not in SUPPORTED_FRAMES:
        raise ValueError(
            f"unknown/unsupported frame {name!r}; supported: {', '.join(SUPPORTED_FRAMES)}"
        )
    return key


def get_frame(name: str = DEFAULT_FRAME) -> type[BaseCoordinateFrame]:
    """Return the Astropy frame class for a supported frame name."""
    coord = get_coordinates()
    key = normalize_frame_name(name)
    mapping = {
        "icrs": coord.ICRS,
        "galactic": coord.Galactic,
        "fk5": coord.FK5,
        "fk4": coord.FK4,
    }
    return mapping[key]
