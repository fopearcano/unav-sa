#!/usr/bin/env python3
"""CLI: inspect a local UNAV-SA SQLite database.

Prints the dataset count, object count, and per-source / per-object-type counts.

Example:
    python tools/db_info.py --db data/unav.db
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import typer  # noqa: E402
from rich.console import Console  # noqa: E402

from unav_core.config import load_config  # noqa: E402
from unav_core.db import get_db_info  # noqa: E402

app = typer.Typer(add_completion=False, help=__doc__)
console = Console()
_CONFIG = load_config()


@app.command()
def main(
    db: Path = typer.Option(_CONFIG.database_path, "--db", help="SQLite database path."),
) -> None:
    """Print a summary of the database at ``--db``."""
    info = get_db_info(db)
    console.print(f"[bold]{info['database']}[/bold]")
    console.print(f"  datasets: {info['dataset_count']}")
    console.print(f"  objects:  {info['object_count']}")

    if info["datasets"]:
        console.print("  [dim]datasets:[/dim]")
        for d in info["datasets"]:
            console.print(f"    - {d['name']} ({d['source']}): {d['objects']}")

    if info["by_source"]:
        console.print("  [dim]by source:[/dim]")
        for source, count in info["by_source"].items():
            console.print(f"    - {source}: {count}")

    if info["by_type"]:
        console.print("  [dim]by object type:[/dim]")
        for object_type, count in info["by_type"].items():
            console.print(f"    - {object_type}: {count}")


if __name__ == "__main__":
    app()
