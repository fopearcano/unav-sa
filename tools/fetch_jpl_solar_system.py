#!/usr/bin/env python3
"""CLI: fetch several solar-system bodies from JPL Horizons into one JSONL file.

Example:
    python tools/fetch_jpl_solar_system.py \\
        --epoch 2026-01-01T00:00:00 \\
        --bodies Mercury,Venus,Earth,Mars,Jupiter,Saturn,Uranus,Neptune,Pluto,Moon \\
        --output data/catalogs/jpl_solar_system.jsonl \\
        --db data/unav.db --dataset-name jpl_solar_system_2026

``--bodies`` is comma-separated; each item is a ``name`` (well-known planets/moons
are classified automatically) or ``name=type`` (type in
planet/moon/asteroid/comet/unknown). Requires the optional ``astroquery``
dependency and network access. See ``docs/JPL_SOLAR_SYSTEM_WORKFLOW.md``.
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
from unav_core.connectors.jpl import (  # noqa: E402
    DEFAULT_CENTER,
    classify_body,
    fetch_jpl_solar_system,
)
from unav_core.data.io import write_jsonl  # noqa: E402

app = typer.Typer(add_completion=False, help=__doc__)
console = Console()


def _parse_bodies(raw: str) -> dict[str, str]:
    """Parse ``--bodies`` into ``{name: type}``; plain names are classified."""
    bodies: dict[str, str] = {}
    for item in raw.split(","):
        token = item.strip()
        if not token:
            continue
        if "=" in token:
            name, _, otype = token.partition("=")
            bodies[name.strip()] = otype.strip() or "unknown"
        else:
            bodies[token] = classify_body(token).value
    if not bodies:
        raise typer.BadParameter("no bodies given")
    return bodies


@app.command()
def main(
    epoch: str = typer.Option(..., "--epoch", help="Julian Date or ISO-8601 time."),
    bodies: str = typer.Option(..., "--bodies", help="Comma-separated name or name=type list."),
    center: str = typer.Option(DEFAULT_CENTER, "--center", help="Horizons observer/location."),
    output: Path = typer.Option(..., "--output", "-o", help="Output JSONL path."),
    db: Path | None = typer.Option(
        None, "--db", help="Optional SQLite DB to import the result into."
    ),
    dataset_name: str = typer.Option(
        "jpl_solar_system", "--dataset-name", help="Dataset name to record when importing (--db)."
    ),
) -> None:
    """Fetch several JPL bodies at one epoch, write JSONL, and optionally import."""
    parsed = _parse_bodies(bodies)
    try:
        objects = fetch_jpl_solar_system(parsed, epoch, center)
    except ConnectorError as exc:
        console.print(f"[red]JPL fetch failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    written = write_jsonl(objects, output)
    console.print(f"[green]Wrote {written} objects[/green] to {output}")

    if db is not None:
        from unav_core.db import import_jsonl_to_db

        summary = import_jsonl_to_db(output, db, dataset_name, enrich=True)
        console.print(
            f"[green]Imported {summary.inserted}[/green] object(s) into {db} "
            f"(dataset '{dataset_name}')"
        )
        if summary.duplicates_existing:
            console.print(
                f"[dim]skipped {summary.duplicates_existing} already-present uid(s)[/dim]"
            )


if __name__ == "__main__":
    app()
