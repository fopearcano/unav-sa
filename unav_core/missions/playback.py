"""Deterministic mission playback: evaluate the camera at a time or progress.

The timeline is, for each segment in order: a *transition* phase that linearly
interpolates the camera from the previous segment's pose to this one's (skipped
for the first segment), then a *hold* phase at this pose. Evaluation is fully
deterministic (linear interpolation; directions are normalised after lerping).

See ``docs/MISSIONS.md``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from unav_core.navigation.state import NavigatorState
from unav_core.navigation.vector import Vec3

if TYPE_CHECKING:
    from unav_core.missions.mission import Mission

PHASE_START = "start"
PHASE_TRANSITION = "transition"
PHASE_HOLD = "hold"
PHASE_END = "end"


class PlaybackSample(BaseModel):
    """The state of a mission at a moment in its timeline."""

    model_config = ConfigDict(extra="forbid")

    seconds: float
    progress: float
    segment_index: int
    waypoint_id: str
    phase: str
    camera: NavigatorState


def evaluate_at_seconds(mission: Mission, seconds: float) -> PlaybackSample:
    """Evaluate the mission at ``seconds`` along its timeline (clamped)."""
    _require_cameras(mission)
    segments = mission.segments
    total = mission.total_duration_seconds
    time = max(0.0, min(seconds, total))

    elapsed = 0.0
    for index, segment in enumerate(segments):
        if index > 0 and segment.transition_seconds > 0.0:
            if time <= elapsed + segment.transition_seconds:
                local = (time - elapsed) / segment.transition_seconds
                camera = _lerp_state(segments[index - 1].camera, segment.camera, local)
                return _sample(time, total, index, segment.waypoint_id, PHASE_TRANSITION, camera)
            elapsed += segment.transition_seconds

        if time <= elapsed + segment.hold_seconds:
            phase = PHASE_START if index == 0 and time == 0.0 else PHASE_HOLD
            return _sample(time, total, index, segment.waypoint_id, phase, segment.camera)
        elapsed += segment.hold_seconds

    last = segments[-1]
    return _sample(total, total, len(segments) - 1, last.waypoint_id, PHASE_END, last.camera)


def evaluate_at_progress(mission: Mission, progress: float) -> PlaybackSample:
    """Evaluate the mission at normalised ``progress`` in ``[0, 1]`` (clamped)."""
    clamped = max(0.0, min(progress, 1.0))
    return evaluate_at_seconds(mission, clamped * mission.total_duration_seconds)


def _require_cameras(mission: Mission) -> None:
    if not mission.has_cameras():
        raise ValueError("mission playback requires a camera on every segment")


def _sample(
    seconds: float,
    total: float,
    segment_index: int,
    waypoint_id: str,
    phase: str,
    camera: NavigatorState,
) -> PlaybackSample:
    progress = 0.0 if total <= 0.0 else max(0.0, min(seconds / total, 1.0))
    return PlaybackSample(
        seconds=seconds,
        progress=progress,
        segment_index=segment_index,
        waypoint_id=waypoint_id,
        phase=phase,
        camera=camera,
    )


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _lerp_vec(a: Vec3, b: Vec3, t: float) -> Vec3:
    return Vec3(x=_lerp(a.x, b.x, t), y=_lerp(a.y, b.y, t), z=_lerp(a.z, b.z, t))


def _lerp_direction(a: Vec3, b: Vec3, t: float, fallback: Vec3) -> Vec3:
    blended = _lerp_vec(a, b, t)
    if blended.length_squared() == 0.0:
        return fallback.normalized()
    return blended.normalized()


def _lerp_state(a: NavigatorState, b: NavigatorState, t: float) -> NavigatorState:
    nearest = b if t >= 0.5 else a
    return NavigatorState(
        position=_lerp_vec(a.position, b.position, t),
        direction=_lerp_direction(a.direction, b.direction, t, fallback=b.direction),
        up=_lerp_direction(a.up, b.up, t, fallback=b.up),
        fov_degrees=_lerp(a.fov_degrees, b.fov_degrees, t),
        near_distance=_lerp(a.near_distance, b.near_distance, t),
        far_distance=_lerp(a.far_distance, b.far_distance, t),
        cone_angle_degrees=_lerp(a.cone_angle_degrees, b.cone_angle_degrees, t),
        epoch=nearest.epoch,
        max_visible_objects=nearest.max_visible_objects,
        active_dataset_ids=list(nearest.active_dataset_ids),
    )
