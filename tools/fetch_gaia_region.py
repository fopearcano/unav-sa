#!/usr/bin/env python3
"""CLI: fetch a regional Gaia DR3 cone, normalise it, and (optionally) import it.

Examples:
    # fetch a small region to JSONL
    python tools/fetch_gaia_region.py --ra 56.75 --dec 24.12 \\
        --radius-deg 0.2 --limit 500 --output data/catalogs/gaia_test.jsonl

    # ... and import straight into the local DB (enriched x/y/z)
    python tools/fetch_gaia_region.py --ra 56.75 --dec 24.12 \\
        --radius-deg 0.2 --limit 500 --output data/catalogs/gaia_test.jsonl \\
        --db data/unav.db --dataset-name gaia_test

Regional and limited by design (default limit 500; a large radius is refused
unless --allow-large-radius). Requires the optional ``astroquery`` dependency and
network access; a missing install fails with a clear, actionable message. See
``docs/GAIA_WORKFLOW.md``.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import typer  # noqa: E402
from rich.console import Console  # noqa: E402

from unav_core.connectors.base import (  # noqa: E402
    DEFAULT_GAIA_LIMIT,
    HARD_WARN_LIMIT,
    ConnectorError,
)
from unav_core.connectors.gaia import fetch_gaia_region  # noqa: E402
from unav_core.data.io import write_jsonl  # noqa: E402

app = typer.Typer(add_completion=False, help=__doc__)
console = Console()


@app.command()
def main(
    ra: float = typer.Option(..., "--ra", help="Cone centre RA (deg)."),
    dec: float = typer.Option(..., "--dec", help="Cone centre Dec (deg)."),
    radius_deg: float = typer.Option(0.1, "--radius-deg", "--radius", help="Cone radius (deg)."),
    limit: int = typer.Option(
        DEFAULT_GAIA_LIMIT, "--limit", help=f"Max rows (default {DEFAULT_GAIA_LIMIT})."
    ),
    output: Path = typer.Option(..., "--output", "-o", help="Output JSONL path."),
    db: Path | None = typer.Option(
        None, "--db", help="Optional SQLite DB to import the result into."
    ),
    dataset_name: str = typer.Option(
        "gaia", "--dataset-name", help="Dataset name to record when importing (--db)."
    ),
    allow_large_radius: bool = typer.Option(
        False, "--allow-large-radius", help="Override the safe radius cap (discouraged)."
    ),
) -> None:
    """Fetch a Gaia region to ``--output`` and optionally import it into ``--db``."""
    if limit > HARD_WARN_LIMIT:
        console.print(
            f"[yellow]warning:[/yellow] limit {limit} exceeds the safe ceiling of "
            f"{HARD_WARN_LIMIT}; UNAV-SA is for regional, limited fetches — large "
            "downloads are discouraged."
        )

    try:
        objects = fetch_gaia_region(
            ra, dec, radius_deg, limit, allow_large_radius=allow_large_radius
        )
    except ConnectorError as exc:
        console.print(f"[red]Gaia fetch failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    written = write_jsonl(objects, output)
    console.print(f"[green]Wrote {written} Gaia objects[/green] to {output}")

    if db is not None:
        # Import the JSONL we just wrote, enriching Cartesian x/y/z for 3D.
        from unav_core.db import import_jsonl_to_db

        summary = import_jsonl_to_db(output, db, dataset_name, enrich=True)
        console.print(
            f"[green]Imported {summary.inserted}[/green] object(s) into {db} "
            f"(dataset '{dataset_name}', enriched x/y/z)"
        )
        if summary.duplicates_existing:
            console.print(
                f"[dim]skipped {summary.duplicates_existing} already-present uid(s)[/dim]"
            )


if __name__ == "__main__":
    app()
