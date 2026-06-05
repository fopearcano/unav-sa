"""Build the UNAV camera rig + waypoint nulls in a Cinema 4D scene.

**Cinema 4D side** — this module imports ``c4d`` and only runs inside Cinema 4D.
It owns the UNAV->C4D coordinate mapping (via :mod:`client`) and the creation of
host objects; it contains **no** astronomy and **no** networking. Skeleton level:
it builds a camera rig and waypoint nulls from a camera-path dict produced by
:mod:`client`.

See ``adapters/cinema4d/docs/C4D_ADAPTER_MVP.md`` and ``C4D_ADAPTER_LIMITATIONS.md``.
"""

from __future__ import annotations

import c4d

# Sibling import: the .pyp adds the plugin folder to sys.path; support both forms.
try:  # pragma: no cover - import shape depends on how C4D loads the plugin
    from . import client
except ImportError:  # pragma: no cover
    import client

RIG_NAME = "UNAV_CameraRig"
CAMERA_NAME = "UNAV_Camera"
WAYPOINTS_GROUP_NAME = "UNAV_Waypoints"


def _vec(position, scale):
    """A C4D vector from a UNAV position dict ``{x, y, z}`` (parsecs)."""
    cx, cy, cz = client.unav_to_c4d(position["x"], position["y"], position["z"], scale)
    return c4d.Vector(cx, cy, cz)


def build_camera_rig(doc, camera_path, *, scale=client.DEFAULT_SCALE, make_waypoints=True):
    """Create ``UNAV_CameraRig`` (null) containing a camera and optional waypoints.

    ``doc`` is the active ``c4d.documents.BaseDocument``; ``camera_path`` is the
    dict from ``client.mission_camera_path`` / ``derive_camera_path``. Returns
    ``(rig, camera, waypoint_nulls)``. Does not key anything — see
    :mod:`timeline_bake` for the timeline.
    """
    doc.StartUndo()

    rig = c4d.BaseObject(c4d.Onull)
    rig.SetName(RIG_NAME)
    doc.InsertObject(rig)
    doc.AddUndo(c4d.UNDOTYPE_NEW, rig)

    camera = c4d.CameraObject()
    camera.SetName(CAMERA_NAME)
    doc.InsertObject(camera, parent=rig)
    doc.AddUndo(c4d.UNDOTYPE_NEW, camera)

    # Place the camera at the first key that has a position (a sensible start pose).
    first = next((k for k in camera_path.get("keys", []) if client.key_position(k)), None)
    if first is not None:
        camera.SetAbsPos(_vec(client.key_position(first), scale))

    waypoint_nulls = []
    if make_waypoints:
        group = c4d.BaseObject(c4d.Onull)
        group.SetName(WAYPOINTS_GROUP_NAME)
        doc.InsertObject(group, parent=rig)
        doc.AddUndo(c4d.UNDOTYPE_NEW, group)
        for key in camera_path.get("keys", []):
            position = client.key_position(key)
            if position is None:
                continue
            null = c4d.BaseObject(c4d.Onull)
            null.SetName(key.get("label") or key.get("waypoint_id") or f"wp{key['index']}")
            null.SetAbsPos(_vec(position, scale))
            doc.InsertObject(null, parent=group)
            doc.AddUndo(c4d.UNDOTYPE_NEW, null)
            waypoint_nulls.append(null)

    doc.EndUndo()
    c4d.EventAdd()
    return rig, camera, waypoint_nulls
