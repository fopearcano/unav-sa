#!/usr/bin/env python3
"""CLI: fetch a regional Gaia DR3 cone and write normalised JSONL.

Example:
    python tools/fetch_gaia_region.py --ra 45.0 --dec 0.0 --radius 0.1 \\
        --limit 500 --output data/gaia_region.jsonl

Requires the optional ``astroquery`` dependency and network access.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import typer  # noqa: E402
from rich.console import Console  # noqa: E402

from unav_core.connectors.base import DEFAULT_GAIA_LIMIT, ConnectorError  # noqa: E402
from unav_core.connectors.gaia import fetch_gaia_region  # noqa: E402
from unav_core.data.io import write_jsonl  # noqa: E402

app = typer.Typer(add_completion=False, help=__doc__)
console = Console()


@app.command()
def main(
    ra: float = typer.Option(..., "--ra", help="Cone centre RA (deg)."),
    dec: float = typer.Option(..., "--dec", help="Cone centre Dec (deg)."),
    radius: float = typer.Option(0.1, "--radius", help="Cone radius (deg)."),
    limit: int = typer.Option(DEFAULT_GAIA_LIMIT, "--limit", help="Max rows."),
    output: Path = typer.Option(..., "--output", "-o", help="Output JSONL path."),
    allow_large_radius: bool = typer.Option(
        False, "--allow-large-radius", help="Override the safe radius cap."
    ),
) -> None:
    """Fetch a Gaia region and write it to ``--output``."""
    try:
        objects = fetch_gaia_region(ra, dec, radius, limit, allow_large_radius=allow_large_radius)
    except ConnectorError as exc:
        console.print(f"[red]Gaia fetch failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    written = write_jsonl(objects, output)
    console.print(f"[green]Wrote {written} Gaia objects[/green] to {output}")


if __name__ == "__main__":
    app()
