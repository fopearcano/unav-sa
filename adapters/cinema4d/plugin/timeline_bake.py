"""Bake a UNAV camera path onto a Cinema 4D camera's timeline.

**Cinema 4D side** — imports ``c4d``; runs only inside Cinema 4D. Skeleton level:
it keys **position** at each camera-path frame, and **rotation** when the key has a
view direction (via ``c4d.utils.VectorToHPB``). It contains no astronomy and no
networking — it consumes the camera-path dict from :mod:`client` and lets C4D
interpolate between keys (linear ≈ UNAV's deterministic playback).

See ``adapters/cinema4d/docs/C4D_ADAPTER_MVP.md`` and ``C4D_ADAPTER_LIMITATIONS.md``.
"""

from __future__ import annotations

import c4d

try:  # pragma: no cover - import shape depends on how C4D loads the plugin
    from . import client
except ImportError:  # pragma: no cover
    import client


def _component_descid(base_id, component_id):
    """A DescID for one vector component of a base object parameter."""
    return c4d.DescID(
        c4d.DescLevel(base_id, c4d.DTYPE_VECTOR, 0),
        c4d.DescLevel(component_id, c4d.DTYPE_REAL, 0),
    )


def _ensure_track(obj, descid):
    track = obj.FindCTrack(descid)
    if track is None:
        track = c4d.CTrack(obj, descid)
        obj.InsertTrackSorted(track)
    return track


def _set_key(obj, descid, value, btime):
    """Add/overwrite one keyframe (value at btime) on ``obj``'s parameter track."""
    track = _ensure_track(obj, descid)
    curve = track.GetCurve()
    added = curve.AddKey(btime)
    key = added["key"]
    key.SetValue(curve, value)
    # Linear interpolation matches UNAV playback most closely.
    key.SetInterpolation(curve, c4d.CINTERPOLATION_LINEAR)


def _key_vector(obj, base_id, vector, btime):
    for component_id, value in (
        (c4d.VECTOR_X, vector.x),
        (c4d.VECTOR_Y, vector.y),
        (c4d.VECTOR_Z, vector.z),
    ):
        _set_key(obj, _component_descid(base_id, component_id), value, btime)


def bake_camera_path(doc, camera, camera_path, *, scale=client.DEFAULT_SCALE):
    """Bake position (and rotation where available) keyframes onto ``camera``.

    Returns the number of keyed frames. Keys whose position cannot be resolved are
    skipped. ``camera_path`` is the dict from ``client.mission_camera_path``.
    """
    fps = int(camera_path.get("fps") or doc.GetFps())
    doc.StartUndo()
    doc.AddUndo(c4d.UNDOTYPE_CHANGE, camera)

    keyed = 0
    for key in camera_path.get("keys", []):
        position = client.key_position(key)
        if position is None:
            continue
        btime = c4d.BaseTime(int(key["frame"]), fps)

        cx, cy, cz = client.unav_to_c4d(position["x"], position["y"], position["z"], scale)
        _key_vector(camera, c4d.ID_BASEOBJECT_REL_POSITION, c4d.Vector(cx, cy, cz), btime)

        direction = client.key_direction(key)
        if direction is not None:
            dx, dy, dz = client.unav_to_c4d(direction["x"], direction["y"], direction["z"], 1.0)
            hpb = c4d.utils.VectorToHPB(c4d.Vector(dx, dy, dz))
            _key_vector(camera, c4d.ID_BASEOBJECT_REL_ROTATION, hpb, btime)

        keyed += 1

    doc.EndUndo()
    c4d.EventAdd()
    return keyed
