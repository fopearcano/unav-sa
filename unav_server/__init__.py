"""UNAV-SA local server: API and adapter communication.

``unav_server`` exposes :mod:`unav_core` over a **local API** for the standalone
app and for DCC **adapters**:

* a local HTTP API (FastAPI/uvicorn — *optional* dependencies);
* future WebSocket **state sync** for real-time navigation;
* the communication endpoint that adapters connect to.

It is a thin transport/orchestration layer over the core — no astronomy logic
lives here. FastAPI is imported lazily (via :func:`create_app`), so importing
``unav_server`` itself stays dependency-light.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from unav_server.app import create_app

__all__ = ["create_app"]


def __getattr__(name: str) -> object:
    # Lazy export so ``import unav_server`` never requires FastAPI; it is pulled
    # in only when the app is actually built.
    if name == "create_app":
        from unav_server.app import create_app

        return create_app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
