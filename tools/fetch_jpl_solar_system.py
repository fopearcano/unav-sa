#!/usr/bin/env python3
"""CLI: fetch several solar-system bodies from JPL Horizons into one JSONL file.

Example:
    python tools/fetch_jpl_solar_system.py \\
        --bodies "199=planet,299=planet,499=planet" \\
        --epoch 2451545.0 --center @sun --output data/planets.jsonl

``--bodies`` is comma-separated; each item is ``name`` or ``name=type``
(type in planet/moon/asteroid/comet/unknown). Requires the optional
``astroquery`` dependency and network access.
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
from unav_core.connectors.jpl import DEFAULT_CENTER, fetch_jpl_solar_system  # noqa: E402
from unav_core.data.io import write_jsonl  # noqa: E402

app = typer.Typer(add_completion=False, help=__doc__)
console = Console()


def _parse_bodies(raw: str) -> dict[str, str]:
    bodies: dict[str, str] = {}
    for item in raw.split(","):
        token = item.strip()
        if not token:
            continue
        if "=" in token:
            name, _, otype = token.partition("=")
            bodies[name.strip()] = otype.strip() or "unknown"
        else:
            bodies[token] = "unknown"
    if not bodies:
        raise typer.BadParameter("no bodies given")
    return bodies


@app.command()
def main(
    bodies: str = typer.Option(..., "--bodies", help="Comma-separated name or name=type list."),
    epoch: str = typer.Option(..., "--epoch", help="Julian Date or ISO-8601 time."),
    center: str = typer.Option(DEFAULT_CENTER, "--center", help="Horizons observer/location."),
    output: Path = typer.Option(..., "--output", "-o", help="Output JSONL path."),
) -> None:
    """Fetch several JPL bodies and write them to ``--output``."""
    parsed = _parse_bodies(bodies)
    try:
        objects = fetch_jpl_solar_system(parsed, epoch, center)
    except ConnectorError as exc:
        console.print(f"[red]JPL fetch failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    written = write_jsonl(objects, output)
    console.print(f"[green]Wrote {written} objects[/green] to {output}")


if __name__ == "__main__":
    app()
