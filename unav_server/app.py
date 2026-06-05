"""FastAPI application factory for the UNAV-SA local API.

``create_app(db_path)`` builds a FastAPI app bound to a local database, attaches
a :class:`~unav_server.state_service.StateService` to ``app.state`` and mounts the
API router. It can also serve the standalone static web shell (``unav_app/static``)
at ``/`` so one process serves both the API and the UI.

The server is a thin transport layer over ``unav_core`` — see
``docs/LOCAL_API_SERVER.md`` and ``docs/STANDALONE_APP_SHELL.md``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from unav_core.db.database import PathLike
from unav_server.api import router
from unav_server.state_service import StateService

API_TITLE = "UNAV-SA Local API"
API_VERSION = "0.0.1"

#: Default location of the standalone static web shell (repo-relative).
_DEFAULT_UI_DIR = Path(__file__).resolve().parent.parent / "unav_app" / "static"


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        service: StateService | None = getattr(app.state, "service", None)
        if service is not None:
            service.dispose()


def create_app(
    db_path: PathLike = ":memory:",
    *,
    serve_ui: bool = True,
    ui_directory: PathLike | None = None,
) -> FastAPI:
    """Build a FastAPI app serving ``unav_core`` from the database at ``db_path``.

    When ``serve_ui`` is true and the static UI directory exists, it is mounted at
    ``/`` (the API routes are registered first and take precedence).
    """
    app = FastAPI(title=API_TITLE, version=API_VERSION, lifespan=_lifespan)
    app.state.service = StateService(db_path)
    app.include_router(router)

    ui_dir = Path(ui_directory) if ui_directory is not None else _DEFAULT_UI_DIR
    if serve_ui and ui_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(ui_dir), html=True), name="ui")

    return app
