#!/usr/bin/env python3
"""CLI: import a JSONL catalog file into a local UNAV-SA SQLite database.

Example:
    python tools/import_catalog.py --input samples/sample_catalog.jsonl \\
        --db data/unav.db --dataset-name sample
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running as a plain script from anywhere: put the repo root on sys.path
# so ``import unav_core`` resolves.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import typer  # noqa: E402  (import after sys.path setup)
from rich.console import Console  # noqa: E402

from unav_core.db.importer import import_jsonl_to_db  # noqa: E402

app = typer.Typer(add_completion=False, help=__doc__)
console = Console()


@app.command()
def main(
    input: Path = typer.Option(
        ...,
        "--input",
        "-i",
        exists=True,
        dir_okay=False,
        readable=True,
        help="Input JSONL catalog file.",
    ),
    db: Path = typer.Option(
        ...,
        "--db",
        help="SQLite database path (created if missing).",
    ),
    dataset_name: str = typer.Option(
        ...,
        "--dataset-name",
        help="Label for this import.",
    ),
    enrich: bool = typer.Option(
        False,
        "--enrich/--no-enrich",
        help="Compute Cartesian x/y/z via Astropy during import.",
    ),
) -> None:
    """Import ``--input`` into the SQLite database at ``--db``."""
    summary = import_jsonl_to_db(input, db, dataset_name, enrich=enrich)
    console.print(summary.render())
    if summary.parse_errors:
        console.print(f"[yellow]{summary.parse_errors} line(s) skipped due to errors.[/yellow]")
    console.print(f"[green]Database:[/green] {db}")


if __name__ == "__main__":
    app()
