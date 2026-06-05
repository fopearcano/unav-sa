#!/usr/bin/env python3
"""CLI: fetch a regional SDSS query and write normalised JSONL.

Example:
    python tools/fetch_sdss_region.py --ra 150.0 --dec 2.2 --radius 0.05 \\
        --limit 500 --spectro --output data/sdss_region.jsonl

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

from unav_core.connectors.base import ConnectorError  # noqa: E402
from unav_core.connectors.sdss import (  # noqa: E402
    DEFAULT_SDSS_LIMIT,
    DEFAULT_SDSS_RADIUS_DEG,
    fetch_sdss_region,
)
from unav_core.data.io import write_jsonl  # noqa: E402

app = typer.Typer(add_completion=False, help=__doc__)
console = Console()


@app.command()
def main(
    ra: float = typer.Option(..., "--ra", help="Cone centre RA (deg)."),
    dec: float = typer.Option(..., "--dec", help="Cone centre Dec (deg)."),
    radius: float = typer.Option(DEFAULT_SDSS_RADIUS_DEG, "--radius", help="Cone radius (deg)."),
    limit: int = typer.Option(DEFAULT_SDSS_LIMIT, "--limit", help="Max rows."),
    spectro: bool = typer.Option(
        True, "--spectro/--photo", help="Spectroscopic (redshift+class) vs photometric."
    ),
    output: Path = typer.Option(..., "--output", "-o", help="Output JSONL path."),
    allow_large_radius: bool = typer.Option(
        False, "--allow-large-radius", help="Override the safe radius cap."
    ),
) -> None:
    """Fetch an SDSS region and write it to ``--output``."""
    try:
        objects = fetch_sdss_region(
            ra, dec, radius, limit, spectro=spectro, allow_large_radius=allow_large_radius
        )
    except ConnectorError as exc:
        console.print(f"[red]SDSS fetch failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    written = write_jsonl(objects, output)
    console.print(f"[green]Wrote {written} SDSS objects[/green] to {output}")


if __name__ == "__main__":
    app()
