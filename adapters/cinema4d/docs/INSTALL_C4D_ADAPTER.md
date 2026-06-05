# Install the Cinema 4D Adapter (skeleton)

How to install and run the UNAV-SA Cinema 4D adapter plugin. It is a **thin
client**: it needs a running UNAV-SA server and uses **only** Cinema 4D's bundled
Python + the standard library — **no `pip`, no extra packages**.

> Skeleton level — see [`C4D_ADAPTER_MVP.md`](C4D_ADAPTER_MVP.md) for scope and
> [`C4D_ADAPTER_LIMITATIONS.md`](C4D_ADAPTER_LIMITATIONS.md) for what it does not
> do yet.

## Prerequisites

1. **A running UNAV-SA server** on your machine:
   ```bash
   pip install -e ".[server]"
   python scripts/run_demo.py        # serves http://127.0.0.1:8765 with sample data
   ```
   (Or `python scripts/run_server.py` against an existing database.) Plan at least
   one **mission** in the app — see
   [`../../../docs/VOYAGE_PLANNING_MVP.md`](../../../docs/VOYAGE_PLANNING_MVP.md).
2. **Cinema 4D** with a Python 3 SDK (R23+/2023+). No additional Python packages
   are required — the adapter is stdlib + `c4d` only.

## Install

1. Copy the **`adapters/cinema4d/plugin/`** folder into Cinema 4D's `plugins`
   directory, e.g.:
   - Windows: `C:\Program Files\Maxon Cinema 4D <ver>\plugins\unav_c4d_adapter\`
   - macOS: `/Applications/Maxon Cinema 4D <ver>/plugins/unav_c4d_adapter/`
   - or your user prefs `plugins/` folder.
   Keep the files together (`unav_c4d_adapter.pyp`, `ui.py`, `client.py`,
   `camera_import.py`, `timeline_bake.py`) — the `.pyp` adds its own folder to
   `sys.path` so the siblings import.
2. **Restart Cinema 4D.**
3. Open the plugin from the **Extensions** menu → *UNAV-SA Adapter*.

> Before any public release, register a unique plugin id at
> <https://plugincafe.maxon.net/> and replace the development placeholder
> `PLUGIN_ID` in `unav_c4d_adapter.pyp`.

## Use

1. In the dialog, set the **Server URL** (default `http://127.0.0.1:8765`).
2. Click **Connect** — the health line shows `ok · N objects` or a clear error.
3. Click **Refresh Missions** and pick a mission.
4. Click **Import Selected Mission Camera Path** — creates a `UNAV_CameraRig`
   (null) with a camera and waypoint nulls.
5. Click **Bake to Timeline** — keys the camera position (and rotation where a
   view direction is available); scrub the timeline to play the voyage.

## Manual test checklist

Run these against a real Cinema 4D + UNAV-SA server.

- [ ] **Server off → clear error.** With no server running, click **Connect**:
      the dialog shows "cannot reach UNAV server … — is it running?" and does not
      freeze. *(Verified outside C4D: the client raises `UnavConnectionError` with
      that message.)*
- [ ] **Server on → connects.** Start the server, click **Connect**: the health
      line shows `ok · N objects`.
- [ ] **Missions list loads.** Click **Refresh Missions**: the combo lists the
      missions planned in UNAV-SA (or "no missions" if none).
- [ ] **Import creates a camera rig.** Select a mission, click **Import**: a
      `UNAV_CameraRig` null appears with a `UNAV_Camera` and `UNAV_Waypoints`.
- [ ] **Bake creates keyframes.** Click **Bake to Timeline**: the camera gets
      position keyframes at the segment frames (and rotation keys when a direction
      is present); the status shows the keyed count.

The non-C4D parts of this flow (connect, list, camera-path derivation, error
handling) are covered automatically by `tests/test_c4d_adapter_client.py` and a
live server exercise; the steps above verify the in-C4D scene operations.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| "cannot reach UNAV server" | start the server (`scripts/run_demo.py`); check the URL/port |
| Plugin not in the Extensions menu | confirm the folder is under `plugins/`; restart C4D; check the Console for load errors |
| "no missions" | plan a mission in UNAV-SA first (see the voyage-planning MVP) |
| Import button disabled | connect and refresh missions first |
| Bake button disabled | import a mission first |
