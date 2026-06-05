#!/usr/bin/env python3
"""CLI: fetch one solar-system body from JPL Horizons and write normalised JSONL.

Example:
    python tools/fetch_jpl_body.py --body Mars --epoch 2026-01-01T00:00:00 \\
        --center 500@10 --output data/catalogs/jpl_mars.jsonl

The body type is classified from its name (planets/moons) unless ``--type`` is
given. Requires the optional ``astroquery`` dependency and network access. See
``docs/JPL_SOLAR_SYSTEM_WORKFLOW.md``.
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
from unav_core.connectors.jpl import DEFAULT_CENTER, classify_body, fetch_jpl_body  # noqa: E402
from unav_core.data.io import write_jsonl  # noqa: E402

app = typer.Typer(add_completion=False, help=__doc__)
console = Console()


@app.command()
def main(
    body: str = typer.Option(..., "--body", help="Horizons body id/name, e.g. 'Mars' or '499'."),
    epoch: str = typer.Option(..., "--epoch", help="Julian Date or ISO-8601 time."),
    center: str = typer.Option(DEFAULT_CENTER, "--center", help="Horizons observer/location."),
    object_type: str | None = typer.Option(
        None, "--type", help="planet/moon/asteroid/comet/unknown (default: classify by name)."
    ),
    output: Path = typer.Option(..., "--output", "-o", help="Output JSONL path."),
    db: Path | None = typer.Option(
        None, "--db", help="Optional SQLite DB to import the result into."
    ),
    dataset_name: str = typer.Option(
        "jpl_body", "--dataset-name", help="Dataset name to record when importing (--db)."
    ),
) -> None:
    """Fetch one JPL body at an epoch, write JSONL, and optionally import."""
    otype = object_type if object_type is not None else classify_body(body).value
    try:
        obj = fetch_jpl_body(body, epoch, center, object_type=otype)
    except ConnectorError as exc:
        console.print(f"[red]JPL fetch failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    write_jsonl([obj], output)
    console.print(f"[green]Wrote 1 object[/green] ({obj.uid}, {obj.object_type.value}) to {output}")

    if db is not None:
        from unav_core.db import import_jsonl_to_db

        summary = import_jsonl_to_db(output, db, dataset_name, enrich=True)
        console.print(
            f"[green]Imported {summary.inserted}[/green] object(s) into {db} "
            f"(dataset '{dataset_name}')"
        )


if __name__ == "__main__":
    app()
