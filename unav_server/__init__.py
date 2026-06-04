"""UNAV-SA local server: API and adapter communication.

``unav_server`` exposes :mod:`unav_core` over a **local API** for the standalone
app and for DCC **adapters**. Planned responsibilities:

* a local HTTP API (FastAPI/uvicorn — *optional* dependencies);
* future WebSocket **state sync** for real-time navigation;
* the communication endpoint that adapters connect to.

It is a thin transport/orchestration layer over the core — no astronomy logic
lives here. Not implemented at this stage of the project.
"""

__all__: list[str] = []
