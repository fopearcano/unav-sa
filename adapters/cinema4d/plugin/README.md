# adapters/cinema4d/plugin/

The Cinema 4D adapter **skeleton** — a thin client that connects to a running
UNAV-SA local server and imports camera/mission data into a C4D scene. It uses
**only** the `c4d` SDK and the Python standard library; it runs **no** astronomy,
fetches **no** catalogs, and owns **no** database (see
[`../docs/C4D_DATA_OWNERSHIP_RULES.md`](../docs/C4D_DATA_OWNERSHIP_RULES.md)).

> Skeleton level: enough to connect, list missions, build a camera rig and bake a
> basic timeline. See [`../docs/C4D_ADAPTER_MVP.md`](../docs/C4D_ADAPTER_MVP.md),
> [`../docs/INSTALL_C4D_ADAPTER.md`](../docs/INSTALL_C4D_ADAPTER.md) and
> [`../docs/C4D_ADAPTER_LIMITATIONS.md`](../docs/C4D_ADAPTER_LIMITATIONS.md).

## Files

| File | Role | Imports |
| --- | --- | --- |
| `unav_c4d_adapter.pyp` | plugin entry — registers a CommandData that opens the dialog | `c4d`, stdlib, siblings |
| `ui.py` | the dialog (server URL, Connect, health, Refresh Missions, Import, Bake) | `c4d`, siblings |
| `client.py` | **stdlib-only** HTTP/JSON client + camera-path derivation + coordinate mapping | stdlib only |
| `camera_import.py` | build `UNAV_CameraRig` null + camera + waypoint nulls | `c4d`, `client` |
| `timeline_bake.py` | bake position/rotation keyframes onto the camera | `c4d`, `client` |

Only `client.py` is pure — it imports nothing beyond the standard library, so it
runs in Cinema 4D's bundled Python **and** can be exercised/tested in plain Python
(`tests/test_c4d_adapter_client.py`). The other modules import `c4d` and only run
inside Cinema 4D.

## What it does (skeleton)

1. **Connect** to `http://127.0.0.1:8765` (configurable) and `GET /health`.
2. **Refresh Missions** → `GET /missions`.
3. **Import** a selected mission's camera path
   (`GET /missions/{id}/camera-path` if available, else derived from
   `GET /missions/{id}`) → build `UNAV_CameraRig` + camera + waypoint nulls.
4. **Bake** position (and rotation where a direction is present) keyframes to the
   timeline.

It can also push the active C4D camera back via `POST /navigator/state`
(`client.set_navigator_state`).

## Hard constraints

`c4d` SDK + Python stdlib **only** — no `requests`, `numpy`, `pydantic`,
`sqlalchemy`, `astropy`, `astroquery`. The HTTP/JSON contract is the boundary; the
science stays in UNAV-SA.
