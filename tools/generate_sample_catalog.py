#!/usr/bin/env python3
"""CLI: generate a tiny, deterministic sample catalog (JSONL).

Example:
    python tools/generate_sample_catalog.py \\
        --count 100 --seed 42 --output samples/sample_catalog.jsonl
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

from unav_core.data.sample_generator import (  # noqa: E402
    DEFAULT_COUNT,
    MAX_COUNT,
    write_sample_catalog,
)

app = typer.Typer(add_completion=False, help=__doc__)
console = Console()


@app.command()
def main(
    count: int = typer.Option(
        DEFAULT_COUNT,
        "--count",
        min=0,
        max=MAX_COUNT,
        help=f"Number of objects to generate (0..{MAX_COUNT}).",
    ),
    seed: int = typer.Option(
        42,
        "--seed",
        help="RNG seed; the same seed yields the same catalog.",
    ),
    enrich: bool = typer.Option(
        True,
        "--enrich/--no-enrich",
        help="Compute ICRS Cartesian x/y/z (Astropy) for objects with a distance.",
    ),
    output: Path = typer.Option(
        ...,
        "--output",
        "-o",
        help="Output JSONL path (parent dirs created).",
    ),
) -> None:
    """Write a deterministic sample catalog of ``--count`` objects to ``--output``."""
    written = write_sample_catalog(output, count, seed=seed, enrich=enrich)
    suffix = " (with x/y/z)" if enrich else ""
    console.print(f"[green]Wrote {written} objects[/green] to {output} (seed={seed}){suffix}.")


if __name__ == "__main__":
    app()
