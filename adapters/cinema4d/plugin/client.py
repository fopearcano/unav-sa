"""Stdlib-only client to the UNAV-SA local server, for the Cinema 4D adapter.

This module is the **only** thing the C4D plugin uses to reach UNAV, and it is
deliberately pure: it imports **only the Python standard library** (``urllib`` +
``json`` + ``math``) so it runs inside Cinema 4D's bundled, often pip-less Python
— and so it can be exercised in plain Python for testing. It contains **no**
Astropy/numpy/requests/sqlalchemy and **no** astronomy logic: the science stays in
UNAV-SA; this is a thin client over the HTTP/JSON boundary.

See ``adapters/cinema4d/docs/C4D_LOCAL_API_PROTOCOL.md``.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

DEFAULT_BASE_URL = "http://127.0.0.1:8765"
DEFAULT_TIMEOUT = 5.0
DEFAULT_FPS = 30

#: Coordinate mapping default: Cinema 4D units per parsec (configurable later).
DEFAULT_SCALE = 1.0


# --- errors (clear, adapter-friendly) ---


class UnavClientError(RuntimeError):
    """Base error for the C4D adapter client."""


class UnavConnectionError(UnavClientError):
    """The UNAV server could not be reached (offline / wrong host/port)."""


class UnavHTTPError(UnavClientError):
    """The server responded with a non-2xx status."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(f"HTTP {status}: {detail}")
        self.status = status
        self.detail = detail


# --- coordinate mapping (pure; the adapter owns the host mapping) ---


def unav_to_c4d(
    x: float, y: float, z: float, scale: float = DEFAULT_SCALE
) -> tuple[float, float, float]:
    """Map UNAV ICRS parsecs (right-handed) to C4D units (left-handed, Y-up).

    ``C4D.X = scale*x``, ``C4D.Y = scale*z`` (celestial north -> scene up),
    ``C4D.Z = scale*y``. The y<->z swap is an odd permutation, so it also flips
    handedness (no extra mirror). See ``C4D_ADAPTER_PLAN.md``.
    """
    return (scale * x, scale * z, scale * y)


def c4d_to_unav(
    x: float, y: float, z: float, scale: float = DEFAULT_SCALE
) -> tuple[float, float, float]:
    """Inverse of :func:`unav_to_c4d`: ``unav.(x,y,z) = (C4D.X, C4D.Z, C4D.Y)/scale``."""
    s = scale or 1.0
    return (x / s, z / s, y / s)


# --- camera-path derivation (pure; works on a mission dict) ---


def derive_camera_path(mission: dict[str, Any], fps: int = DEFAULT_FPS) -> dict[str, Any]:
    """Build a camera path from a ``Mission`` dict (the MVP fallback derivation).

    Mirrors the proposed ``GET /missions/{id}/camera-path`` shape and adds a
    *resolved* ``position``/``direction``/``up`` per key: the segment's camera pose
    when present, else the referenced route waypoint's cached position. Timing
    follows UNAV playback (the first segment's transition is ignored). All
    coordinates stay in **UNAV space** (parsecs); the scene mapping happens in C4D.
    """
    route = mission.get("route") or {}
    waypoints = {w.get("wid"): w for w in route.get("waypoints", [])}
    keys: list[dict[str, Any]] = []
    t = 0.0
    for index, segment in enumerate(mission.get("segments", [])):
        if index > 0:
            t += float(segment.get("transition_seconds") or 0.0)
        camera = segment.get("camera")
        waypoint = waypoints.get(segment.get("waypoint_id"))
        position = direction = up = None
        if camera:
            position, direction, up = (
                camera.get("position"),
                camera.get("direction"),
                camera.get("up"),
            )
        if position is None and waypoint:
            position = waypoint.get("position")
        keys.append(
            {
                "index": index,
                "waypoint_id": segment.get("waypoint_id"),
                "time_seconds": t,
                "frame": round(t * fps),
                "hold_seconds": float(segment.get("hold_seconds") or 0.0),
                "camera": camera,
                "position": position,
                "direction": direction,
                "up": up,
                "label": waypoint.get("label") if waypoint else None,
            }
        )
        t += float(segment.get("hold_seconds") or 0.0)
    return {
        "mission_id": mission.get("mission_id"),
        "fps": fps,
        "total_seconds": t,
        "keys": keys,
    }


def key_position(key: dict[str, Any]) -> dict[str, float] | None:
    """Resolve a key's UNAV position from its ``position`` or its ``camera``."""
    if key.get("position"):
        return key["position"]
    camera = key.get("camera")
    return camera.get("position") if camera else None


def key_direction(key: dict[str, Any]) -> dict[str, float] | None:
    """Resolve a key's UNAV view direction from ``direction`` or its ``camera``."""
    if key.get("direction"):
        return key["direction"]
    camera = key.get("camera")
    return camera.get("direction") if camera else None


# --- the HTTP client ---


class UnavClient:
    """A thin stdlib HTTP/JSON client for the UNAV-SA local server."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: float = DEFAULT_TIMEOUT) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # -- transport --

    def _request(self, method: str, path: str, body: Any | None = None) -> Any:
        url = self.base_url + path
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raise UnavHTTPError(exc.code, _error_detail(exc)) from exc
        except urllib.error.URLError as exc:
            raise UnavConnectionError(
                f"cannot reach UNAV server at {self.base_url} — is it running? ({exc.reason})"
            ) from exc
        return json.loads(raw) if raw else None

    def _get(self, path: str) -> Any:
        return self._request("GET", path)

    def _post(self, path: str, body: Any) -> Any:
        return self._request("POST", path, body)

    # -- endpoints (MVP) --

    def health(self) -> dict[str, Any]:
        """``GET /health`` — gate every action on this."""
        return self._get("/health")

    def list_routes(self) -> list[dict[str, Any]]:
        return self._get("/routes")

    def list_missions(self) -> list[dict[str, Any]]:
        return self._get("/missions")

    def get_mission(self, mission_id: str) -> dict[str, Any]:
        return self._get("/missions/" + urllib.parse.quote(mission_id))

    def get_navigator_state(self) -> dict[str, Any]:
        return self._get("/navigator/state")

    def set_navigator_state(self, state: dict[str, Any]) -> dict[str, Any]:
        """``POST /navigator/state`` — push the active C4D camera pose back."""
        return self._post("/navigator/state", state)

    def mission_camera_path(self, mission_id: str, fps: int = DEFAULT_FPS) -> dict[str, Any]:
        """Get a mission's camera path.

        Tries the proposed ``GET /missions/{id}/camera-path`` convenience; if it is
        not available (``404``), falls back to ``GET /missions/{id}`` and derives
        the path client-side (see :func:`derive_camera_path`).
        """
        quoted = urllib.parse.quote(mission_id)
        try:
            return self._get(f"/missions/{quoted}/camera-path?fps={int(fps)}")
        except UnavHTTPError as exc:
            if exc.status == 404:
                return derive_camera_path(self.get_mission(mission_id), fps=fps)
            raise


def _error_detail(exc: urllib.error.HTTPError) -> str:
    try:
        payload = json.loads(exc.read().decode("utf-8"))
        if isinstance(payload, dict) and "detail" in payload:
            return str(payload["detail"])
    except (ValueError, OSError):
        pass
    return getattr(exc, "reason", "") or "request failed"
