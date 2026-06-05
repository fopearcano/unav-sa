"""FastAPI application factory for the UNAV-SA local API.

``create_app(db_path)`` builds a FastAPI app bound to a local database, attaches
a :class:`~unav_server.state_service.StateService` to ``app.state`` and mounts the
API router. The server is a thin transport layer over ``unav_core`` — see
``docs/LOCAL_API_SERVER.md`` and ``docs/ADAPTER_COMMUNICATION_MODEL.md``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from unav_core.db.database import PathLike
from unav_server.api import router
from unav_server.state_service import StateService

API_TITLE = "UNAV-SA Local API"
API_VERSION = "0.0.1"


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        service: StateService | None = getattr(app.state, "service", None)
        if service is not None:
            service.dispose()


def create_app(db_path: PathLike = ":memory:") -> FastAPI:
    """Build a FastAPI app serving ``unav_core`` from the database at ``db_path``."""
    app = FastAPI(title=API_TITLE, version=API_VERSION, lifespan=_lifespan)
    app.state.service = StateService(db_path)
    app.include_router(router)
    return app
