"""Missions: saved navigation sessions and scenarios.

Models **missions** — higher-level, persistable scenarios that compose one or
more :mod:`unav_core.routes`, target sets, timing and navigation parameters into
a reproducible session. Missions are serialisable via :mod:`unav_core.export`
and carry provenance for the data they reference.
"""

from unav_core.missions.mission import Mission, MissionSegment
from unav_core.missions.playback import (
    PlaybackSample,
    evaluate_at_progress,
    evaluate_at_seconds,
)

__all__ = [
    "Mission",
    "MissionSegment",
    "PlaybackSample",
    "evaluate_at_progress",
    "evaluate_at_seconds",
]
