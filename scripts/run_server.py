#!/usr/bin/env python3
"""Run the UNAV-SA local API server (which also serves the standalone UI).

Serves the configured database (does not generate data — use ``run_demo.py`` for
the full prepare + serve flow, or ``setup_dev.py`` to create sample data first).
Host/port/DB default to the local configuration (overridable with ``UNAV_*`` env
vars or the flags below).

    python scripts/run_server.py
    python scripts/run_server.py --db data/unav.db --port 8765

Needs the optional server extras: pip install -e ".[server]". See
``docs/DEVELOPER_WORKFLOW.md``.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import typer  # noqa: E402
from rich.console import Console  # noqa: E402

from unav_core.config import apply_dotenv, load_config  # noqa: E402

app = typer.Typer(add_completion=False, help=__doc__)
console = Console()
_CONFIG = load_config()


@app.command()
def main(
    db: Path = typer.Option(_CONFIG.database_path, "--db", help="SQLite database path."),
    host: str = typer.Option(_CONFIG.server_host, "--host", help="Bind address (localhost)."),
    port: int = typer.Option(_CONFIG.server_port, "--port", help="Port to listen on."),
    open_browser: bool = typer.Option(False, "--open", help="Open the UI in a browser."),
) -> None:
    """Start the local API server + UI on the configured database."""
    apply_dotenv(_REPO_ROOT)
    try:
        import uvicorn

        from unav_server.app import create_app
    except ImportError as exc:  # pragma: no cover - depends on optional extras
        console.print(
            "[red]The server needs FastAPI and uvicorn. Install them with:[/red]\n"
            '    pip install -e ".[server]"'
        )
        raise typer.Exit(code=1) from exc

    if not db.exists():
        console.print(
            f"[yellow]note:[/yellow] {db} does not exist yet — the server will start empty. "
            "Run [bold]python scripts/run_demo.py[/bold] to create sample data."
        )

    url = f"http://{host}:{port}/"
    console.print(f"[bold green]UNAV-SA server[/bold green] → open [bold]{url}[/bold]\n")
    if open_browser:
        import webbrowser

        webbrowser.open(url)

    uvicorn.run(create_app(str(db)), host=host, port=port)


if __name__ == "__main__":
    app()
