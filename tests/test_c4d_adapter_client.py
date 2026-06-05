"""Tests for the Cinema 4D adapter's stdlib client (no C4D, no network).

Covers the pure logic — camera-path derivation, coordinate mapping, error
mapping and the camera-path endpoint fallback — and statically guards that the
plugin imports **no** heavy dependencies (the adapter is a thin client).
"""

import ast
import importlib.util
import io
import urllib.error
import urllib.request
from pathlib import Path

import pytest

_PLUGIN_DIR = Path(__file__).resolve().parent.parent / "adapters" / "cinema4d" / "plugin"


def _load_client():
    spec = importlib.util.spec_from_file_location("c4d_client", _PLUGIN_DIR / "client.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


client = _load_client()


# --- coordinate mapping ---


def test_unav_to_c4d_swap_and_scale():
    assert client.unav_to_c4d(1.0, 2.0, 3.0) == (1.0, 3.0, 2.0)  # y<->z swap
    assert client.unav_to_c4d(1.0, 2.0, 3.0, scale=2.0) == (2.0, 6.0, 4.0)


def test_c4d_to_unav_is_inverse():
    assert client.c4d_to_unav(*client.unav_to_c4d(1.0, 2.0, 3.0)) == (1.0, 2.0, 3.0)
    assert client.c4d_to_unav(*client.unav_to_c4d(1.0, 2.0, 3.0, 5.0), 5.0) == (1.0, 2.0, 3.0)


# --- camera-path derivation ---


def _mission_without_cameras():
    return {
        "mission_id": "m1",
        "route": {
            "waypoints": [
                {"wid": "w1", "label": "A", "position": {"x": 0.0, "y": 0.0, "z": 0.0}},
                {"wid": "w2", "label": "B", "position": {"x": 10.0, "y": 0.0, "z": 0.0}},
            ]
        },
        "segments": [
            {"waypoint_id": "w1", "transition_seconds": 0.0, "hold_seconds": 0.0, "camera": None},
            {"waypoint_id": "w2", "transition_seconds": 10.0, "hold_seconds": 0.0, "camera": None},
        ],
    }


def test_derive_path_falls_back_to_waypoint_positions():
    path = client.derive_camera_path(_mission_without_cameras(), fps=30)
    assert path["mission_id"] == "m1"
    assert [k["frame"] for k in path["keys"]] == [0, 300]  # 0s and 10s @ 30fps
    assert [client.key_position(k) for k in path["keys"]] == [
        {"x": 0.0, "y": 0.0, "z": 0.0},
        {"x": 10.0, "y": 0.0, "z": 0.0},
    ]
    assert [client.key_direction(k) for k in path["keys"]] == [None, None]
    assert [k["label"] for k in path["keys"]] == ["A", "B"]


def test_derive_path_uses_segment_camera_when_present():
    mission = _mission_without_cameras()
    mission["segments"][0]["camera"] = {
        "position": {"x": 1.0, "y": 2.0, "z": 3.0},
        "direction": {"x": 0.0, "y": 0.0, "z": -1.0},
        "up": {"x": 0.0, "y": 1.0, "z": 0.0},
    }
    path = client.derive_camera_path(mission)
    key0 = path["keys"][0]
    assert client.key_position(key0) == {"x": 1.0, "y": 2.0, "z": 3.0}  # camera, not waypoint
    assert client.key_direction(key0) == {"x": 0.0, "y": 0.0, "z": -1.0}


def test_derive_path_hold_then_transition_timing():
    mission = _mission_without_cameras()
    mission["segments"][0]["hold_seconds"] = 5.0  # dwell before the next transition
    path = client.derive_camera_path(mission, fps=10)
    # key0 at t=0; key1 at t = hold(5) + transition(10) = 15s -> frame 150
    assert [k["time_seconds"] for k in path["keys"]] == [0.0, 15.0]
    assert path["keys"][1]["frame"] == 150
    assert path["total_seconds"] == 15.0


# --- HTTP error mapping ---


def test_connection_error_is_clear(monkeypatch):
    def boom(request, timeout=None):
        raise urllib.error.URLError("Connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    with pytest.raises(client.UnavConnectionError) as exc:
        client.UnavClient().health()
    assert "cannot reach UNAV server" in str(exc.value)


def test_http_error_carries_status_and_detail(monkeypatch):
    def raise_422(request, timeout=None):
        raise urllib.error.HTTPError(
            url="http://x/navigator/state",
            code=422,
            msg="Unprocessable",
            hdrs=None,
            fp=io.BytesIO(b'{"detail": "must be a non-zero vector"}'),
        )

    monkeypatch.setattr(urllib.request, "urlopen", raise_422)
    with pytest.raises(client.UnavHTTPError) as exc:
        client.UnavClient().set_navigator_state({"direction": {"x": 0, "y": 0, "z": 0}})
    assert exc.value.status == 422
    assert "non-zero vector" in exc.value.detail


# --- camera-path endpoint vs. fallback ---


def test_camera_path_uses_endpoint_when_available():
    c = client.UnavClient()
    c._get = lambda path: {"mission_id": "m1", "fps": 30, "keys": ["from-endpoint"]}
    assert c.mission_camera_path("m1")["keys"] == ["from-endpoint"]


def test_camera_path_falls_back_on_404():
    c = client.UnavClient()
    mission = _mission_without_cameras()

    def fake_get(path):
        if "/camera-path" in path:
            raise client.UnavHTTPError(404, "not found")
        if path.startswith("/missions/"):
            return mission
        raise AssertionError(path)

    c._get = fake_get
    path = c.mission_camera_path("m1")
    assert path["mission_id"] == "m1"
    assert len(path["keys"]) == 2  # derived from the mission


# --- static guard: no heavy dependencies in the plugin ---

_FORBIDDEN = {
    "numpy",
    "scipy",
    "pandas",
    "requests",
    "httpx",
    "astropy",
    "astroquery",
    "pydantic",
    "sqlalchemy",
    "fastapi",
    "uvicorn",
    "unav_core",
    "unav_server",
}


def _imported_top_level(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


@pytest.mark.parametrize(
    "filename",
    ["unav_c4d_adapter.pyp", "ui.py", "client.py", "camera_import.py", "timeline_bake.py"],
)
def test_plugin_imports_no_heavy_dependencies(filename):
    imported = _imported_top_level(_PLUGIN_DIR / filename)
    assert not (imported & _FORBIDDEN), f"{filename} imports forbidden: {imported & _FORBIDDEN}"


def test_client_module_is_pure_stdlib():
    # The client must not even import c4d (it runs in plain Python and in C4D).
    assert "c4d" not in _imported_top_level(_PLUGIN_DIR / "client.py")
