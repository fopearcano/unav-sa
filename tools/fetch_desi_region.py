#!/usr/bin/env python3
"""CLI: import a local DESI redshift catalog into normalised JSONL.

DESI region *downloading* is intentionally not enabled (UNAV-SA never mirrors
archives). The working pathway is to import a DESI catalog file you already have:

    python tools/fetch_desi_region.py --input zcat.fits --output data/desi.jsonl

Passing --ra/--dec/--radius instead prints guidance toward this file pathway and
the planned public-database workflow (see docs/DESI_CONNECTOR.md).
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import typer  # noqa: E402
from rich.console import Console  # noqa: E402

from unav_core.connectors.base import ConnectorError, ConnectorNotSupportedError  # noqa: E402
from unav_core.connectors.desi import fetch_desi_region, load_desi_file  # noqa: E402
from unav_core.data.io import write_jsonl  # noqa: E402

app = typer.Typer(add_completion=False, help=__doc__)
console = Console()


@app.command()
def main(
    input: Path | None = typer.Option(
        None, "--input", "-i", help="Local DESI catalog file (FITS/ECSV/CSV/VOTable)."
    ),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output JSONL path."),
    ra: float | None = typer.Option(None, "--ra", help="(Region fetch is not enabled.)"),
    dec: float | None = typer.Option(None, "--dec", help="(Region fetch is not enabled.)"),
    radius: float | None = typer.Option(None, "--radius", help="(Region fetch is not enabled.)"),
) -> None:
    """Import a local DESI file (``--input``) and write it to ``--output``."""
    if input is not None:
        if output is None:
            raise typer.BadParameter("--output is required when --input is given")
        try:
            objects = load_desi_file(input)
        except (ConnectorError, FileNotFoundError) as exc:
            console.print(f"[red]DESI import failed:[/red] {exc}")
            raise typer.Exit(code=1) from exc
        written = write_jsonl(objects, output)
        console.print(f"[green]Wrote {written} DESI objects[/green] to {output}")
        return

    # No --input: a region fetch was requested (or nothing). Show the guidance.
    try:
        fetch_desi_region(ra or 0.0, dec or 0.0, radius or 0.0)
    except ConnectorNotSupportedError as exc:
        console.print(f"[yellow]{exc}[/yellow]")
        raise typer.Exit(code=1) from exc


if __name__ == "__main__":
    app()
