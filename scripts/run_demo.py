#!/usr/bin/env python3
"""One-command local demo for UNAV-SA.

Runs the whole MVP vertical slice:

    generate sample catalog (if missing)
    -> import into a local SQLite database (if missing/empty)
    -> start the local API server (which also serves the standalone UI)
    -> print the URL to open

Example:
    python scripts/run_demo.py
    # then open the printed URL, e.g. http://127.0.0.1:8765/

No external network is required and there is no Cinema 4D dependency. Needs the
optional server extras: pip install -e ".[server]".
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import typer  # noqa: E402
from rich.console import Console  # noqa: E402

from unav_core.data.sample_generator import write_sample_catalog  # noqa: E402
from unav_core.db import Database, import_jsonl_to_db  # noqa: E402

app = typer.Typer(add_completion=False, help=__doc__)
console = Console()

_DEFAULT_SAMPLE = _REPO_ROOT / "samples" / "sample_catalog.jsonl"
_DEFAULT_DB = _REPO_ROOT / "data" / "unav.db"


def prepare(*, db: Path, sample: Path, count: int, seed: int, fresh: bool) -> None:
    """Ensure the sample catalog and a populated database exist."""
    if fresh and db.exists():
        db.unlink()
        console.print(f"[yellow]removed existing database[/yellow] {db}")

    # 1. sample catalog
    if sample.exists():
        console.print(f"[green]✓[/green] sample catalog: {sample}")
    else:
        written = write_sample_catalog(sample, count, seed=seed)
        console.print(f"[green]✓[/green] generated {written} objects → {sample}")

    # 2. database (import only when missing or empty)
    needs_import = not db.exists()
    if not needs_import:
        probe = Database(db)
        try:
            needs_import = probe.count_objects() == 0
        finally:
            probe.dispose()

    if needs_import:
        summary = import_jsonl_to_db(sample, db, "sample", enrich=True)
        console.print(
            f"[green]✓[/green] imported {summary.inserted} objects → {db} (enriched x/y/z)"
        )
    else:
        opened = Database(db)
        try:
            existing = opened.count_objects()
        finally:
            opened.dispose()
        console.print(f"[green]✓[/green] database ready: {db} ({existing} objects)")


@app.command()
def main(
    db: Path = typer.Option(_DEFAULT_DB, "--db", help="SQLite database path."),
    host: str = typer.Option("127.0.0.1", "--host", help="Bind address (localhost)."),
    port: int = typer.Option(8765, "--port", help="Port to listen on."),
    count: int = typer.Option(100, "--count", help="Sample objects to generate if missing."),
    seed: int = typer.Option(42, "--seed", help="Sample RNG seed."),
    fresh: bool = typer.Option(False, "--fresh", help="Rebuild the database from scratch."),
    open_browser: bool = typer.Option(False, "--open", help="Open the UI in a browser."),
    no_serve: bool = typer.Option(False, "--no-serve", help="Prepare data and exit (no server)."),
) -> None:
    """Prepare sample data and start the local UNAV-SA demo."""
    prepare(db=db, sample=_DEFAULT_SAMPLE, count=count, seed=seed, fresh=fresh)

    url = f"http://{host}:{port}/"
    if no_serve:
        console.print(f"\n[bold]prepared.[/bold] start the server to open [bold]{url}[/bold]")
        return

    try:
        import uvicorn

        from unav_server.app import create_app
    except ImportError as exc:  # pragma: no cover - depends on optional extras
        console.print(
            "[red]The demo server needs FastAPI and uvicorn. Install them with:[/red]\n"
            '    pip install -e ".[server]"'
        )
        raise typer.Exit(code=1) from exc

    console.print(f"\n[bold green]UNAV-SA demo ready[/bold green] → open [bold]{url}[/bold]\n")
    if open_browser:
        import webbrowser

        webbrowser.open(url)

    uvicorn.run(create_app(str(db)), host=host, port=port)


if __name__ == "__main__":
    app()
