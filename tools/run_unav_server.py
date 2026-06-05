#!/usr/bin/env python3
"""CLI: run the UNAV-SA local API server (FastAPI + uvicorn).

Example:
    python tools/run_unav_server.py --db data/unav.db --port 8765

Requires the optional ``server`` dependencies (``pip install -e ".[server]"``).
The server binds to localhost by default — it is a *local* API.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import typer  # noqa: E402

app = typer.Typer(add_completion=False, help=__doc__)


@app.command()
def main(
    db: str = typer.Option(":memory:", "--db", help="SQLite database path (or ':memory:')."),
    host: str = typer.Option("127.0.0.1", "--host", help="Bind address (localhost by default)."),
    port: int = typer.Option(8765, "--port", help="Port to listen on."),
) -> None:
    """Start the local API server against the database at ``--db``."""
    try:
        import uvicorn

        from unav_server.app import create_app
    except ImportError as exc:  # pragma: no cover - depends on optional extras
        typer.echo(
            "The server requires FastAPI and uvicorn. Install them with:\n"
            '    pip install -e ".[server]"',
            err=True,
        )
        raise typer.Exit(code=1) from exc

    uvicorn.run(create_app(db), host=host, port=port)


if __name__ == "__main__":
    app()
