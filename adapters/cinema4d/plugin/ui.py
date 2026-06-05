"""The Cinema 4D adapter dialog (connect, list missions, import + bake).

**Cinema 4D side** — imports ``c4d``; runs only inside Cinema 4D. It wires the
stdlib :mod:`client` (HTTP/JSON) to the scene builders (:mod:`camera_import`,
:mod:`timeline_bake`). It holds no astronomy and no data — it only drives the
thin client and reports clear status. See ``adapters/cinema4d/docs/``.
"""

from __future__ import annotations

import c4d
from c4d import gui

try:  # pragma: no cover - import shape depends on how C4D loads the plugin
    from . import camera_import, client, timeline_bake
except ImportError:  # pragma: no cover
    import camera_import
    import client
    import timeline_bake

# --- gadget ids ---
_URL_FIELD = 1001
_CONNECT_BTN = 1002
_HEALTH_TEXT = 1003
_REFRESH_BTN = 1004
_MISSION_COMBO = 1005
_IMPORT_BTN = 1006
_BAKE_BTN = 1007
_STATUS_TEXT = 1008

_MISSION_BASE = 20000  # combo entries are _MISSION_BASE + index


class UnavAdapterDialog(gui.GeDialog):
    """A minimal dialog: server URL, Connect, missions, Import, Bake."""

    def __init__(self) -> None:
        super().__init__()
        self.client = None
        self.missions: list[dict] = []
        self.camera_path: dict | None = None
        self.camera = None

    # -- layout --

    def CreateLayout(self) -> bool:
        self.SetTitle("UNAV-SA — Cinema 4D Adapter")

        self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=2)
        self.GroupBorderSpace(8, 8, 8, 8)
        self.AddStaticText(0, c4d.BFH_LEFT, name="Server URL")
        self.AddEditText(_URL_FIELD, c4d.BFH_SCALEFIT)
        self.SetString(_URL_FIELD, client.DEFAULT_BASE_URL)
        self.AddButton(_CONNECT_BTN, c4d.BFH_LEFT, name="Connect")
        self.AddStaticText(_HEALTH_TEXT, c4d.BFH_SCALEFIT, name="not connected")
        self.GroupEnd()

        self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=1)
        self.GroupBorderSpace(8, 0, 8, 8)
        self.AddButton(_REFRESH_BTN, c4d.BFH_LEFT, name="Refresh Missions")
        self.AddComboBox(_MISSION_COMBO, c4d.BFH_SCALEFIT)
        self.AddButton(_IMPORT_BTN, c4d.BFH_LEFT, name="Import Selected Mission Camera Path")
        self.AddButton(_BAKE_BTN, c4d.BFH_LEFT, name="Bake to Timeline")
        self.AddStaticText(_STATUS_TEXT, c4d.BFH_SCALEFIT, name="")
        self.GroupEnd()

        self.Enable(_REFRESH_BTN, False)
        self.Enable(_IMPORT_BTN, False)
        self.Enable(_BAKE_BTN, False)
        return True

    # -- helpers --

    def _status(self, message: str) -> None:
        self.SetString(_STATUS_TEXT, message)

    def _make_client(self):
        return client.UnavClient(self.GetString(_URL_FIELD).strip() or client.DEFAULT_BASE_URL)

    # -- actions --

    def _connect(self) -> None:
        self.client = self._make_client()
        try:
            health = self.client.health()
        except client.UnavClientError as exc:
            self.SetString(_HEALTH_TEXT, "not reachable")
            self._status(str(exc))
            self.Enable(_REFRESH_BTN, False)
            return
        self.SetString(_HEALTH_TEXT, f"ok · {health.get('object_count', 0)} objects")
        self._status("connected")
        self.Enable(_REFRESH_BTN, True)
        self._refresh_missions()

    def _refresh_missions(self) -> None:
        if self.client is None:
            return
        try:
            self.missions = self.client.list_missions()
        except client.UnavClientError as exc:
            self._status(str(exc))
            return
        self.FreeChildren(_MISSION_COMBO)
        for index, mission in enumerate(self.missions):
            self.AddChild(_MISSION_COMBO, _MISSION_BASE + index, mission.get("title", "(untitled)"))
        if self.missions:
            self.SetInt32(_MISSION_COMBO, _MISSION_BASE)
            self.Enable(_IMPORT_BTN, True)
            self._status(f"{len(self.missions)} mission(s)")
        else:
            self.Enable(_IMPORT_BTN, False)
            self._status("no missions — plan one in UNAV-SA first")

    def _selected_mission(self) -> dict | None:
        index = self.GetInt32(_MISSION_COMBO) - _MISSION_BASE
        if 0 <= index < len(self.missions):
            return self.missions[index]
        return None

    def _import(self) -> None:
        mission = self._selected_mission()
        if mission is None or self.client is None:
            return
        try:
            self.camera_path = self.client.mission_camera_path(mission["mission_id"])
        except client.UnavClientError as exc:
            self._status(str(exc))
            return
        doc = c4d.documents.GetActiveDocument()
        _rig, self.camera, nulls = camera_import.build_camera_rig(doc, self.camera_path)
        self.Enable(_BAKE_BTN, True)
        self._status(f"imported '{mission.get('title')}' — {len(nulls)} waypoint(s)")

    def _bake(self) -> None:
        if self.camera is None or self.camera_path is None:
            self._status("import a mission first")
            return
        doc = c4d.documents.GetActiveDocument()
        keyed = timeline_bake.bake_camera_path(doc, self.camera, self.camera_path)
        self._status(f"baked {keyed} keyframe(s) to the timeline")

    # -- dispatch --

    def Command(self, gadget_id: int, msg) -> bool:  # noqa: N802 - C4D SDK signature
        if gadget_id == _CONNECT_BTN:
            self._connect()
        elif gadget_id == _REFRESH_BTN:
            self._refresh_missions()
        elif gadget_id == _IMPORT_BTN:
            self._import()
        elif gadget_id == _BAKE_BTN:
            self._bake()
        return True
