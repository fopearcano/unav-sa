#!/usr/bin/env python3
"""CLI: fetch one solar-system body from JPL Horizons and write normalised JSONL.

Example:
    python tools/fetch_jpl_body.py --body 499 --epoch 2451545.0 \\
        --center @sun --type planet --output data/mars.jsonl

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
from unav_core.connectors.jpl import DEFAULT_CENTER, fetch_jpl_body  # noqa: E402
from unav_core.data.io import write_jsonl  # noqa: E402

app = typer.Typer(add_completion=False, help=__doc__)
console = Console()


@app.command()
def main(
    body: str = typer.Option(..., "--body", help="Horizons body id/name, e.g. '499'."),
    epoch: str = typer.Option(..., "--epoch", help="Julian Date or ISO-8601 time."),
    center: str = typer.Option(DEFAULT_CENTER, "--center", help="Horizons observer/location."),
    object_type: str = typer.Option(
        "unknown", "--type", help="planet/moon/asteroid/comet/unknown."
    ),
    output: Path = typer.Option(..., "--output", "-o", help="Output JSONL path."),
) -> None:
    """Fetch one JPL body and write it to ``--output``."""
    try:
        obj = fetch_jpl_body(body, epoch, center, object_type=object_type)
    except ConnectorError as exc:
        console.print(f"[red]JPL fetch failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    write_jsonl([obj], output)
    console.print(f"[green]Wrote 1 object[/green] ({obj.uid}) to {output}")


if __name__ == "__main__":
    app()
