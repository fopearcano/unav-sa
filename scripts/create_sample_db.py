#!/usr/bin/env python3
"""One-command offline sample database for UNAV-SA.

Generates the deterministic sample catalog (if missing), initializes a local
SQLite database, imports the catalog (enriching Cartesian x/y/z), and prints a DB
summary. No network access, no Cinema 4D.

Example:
    python scripts/create_sample_db.py \\
        --catalog samples/sample_catalog.jsonl --db data/unav_sample.db

Then inspect it with: python tools/db_info.py --db data/unav_sample.db
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import typer  # noqa: E402
from rich.console import Console  # noqa: E402

from unav_core.config import load_config  # noqa: E402
from unav_core.data.sample_generator import write_sample_catalog  # noqa: E402
from unav_core.db import Database, get_db_info, import_jsonl_to_db  # noqa: E402

app = typer.Typer(add_completion=False, help=__doc__)
console = Console()

_CONFIG = load_config()
_DEFAULT_DB = _CONFIG.data_dir / "unav_sample.db"


@app.command()
def main(
    catalog: Path = typer.Option(
        _CONFIG.sample_catalog_path,
        "--catalog",
        help="Sample catalog JSONL (generated if missing).",
    ),
    db: Path = typer.Option(_DEFAULT_DB, "--db", help="SQLite database to create/populate."),
    count: int = typer.Option(
        100, "--count", help="Objects to generate if the catalog is missing."
    ),
    seed: int = typer.Option(42, "--seed", help="Sample RNG seed."),
    fresh: bool = typer.Option(False, "--fresh", help="Rebuild the database from scratch."),
) -> None:
    """Generate the sample catalog (if missing), import it into SQLite, summarise."""
    # 1. sample catalog
    if catalog.exists():
        console.print(f"[green]✓[/green] sample catalog: {catalog}")
    else:
        written = write_sample_catalog(catalog, count, seed=seed)
        console.print(f"[green]✓[/green] generated {written} objects → {catalog}")

    # 2. database (rebuild on --fresh; import only when missing or empty)
    if fresh and db.exists():
        db.unlink()
        console.print(f"[yellow]removed existing database[/yellow] {db}")

    needs_import = not db.exists()
    if not needs_import:
        probe = Database(db)
        try:
            needs_import = probe.count_objects() == 0
        finally:
            probe.dispose()

    if needs_import:
        summary = import_jsonl_to_db(catalog, db, "sample", enrich=True)
        console.print(
            f"[green]✓[/green] imported {summary.inserted} objects → {db} (enriched x/y/z)"
        )
    else:
        console.print(f"[green]✓[/green] database already populated: {db}")

    # 3. summary
    info = get_db_info(db)
    console.print(
        f"\n[bold]{info['database']}[/bold] — "
        f"{info['object_count']} objects, {info['dataset_count']} dataset(s)"
    )
    for source, n in info["by_source"].items():
        console.print(f"  {source}: {n}")
    for object_type, n in info["by_type"].items():
        console.print(f"  [dim]{object_type}[/dim]: {n}")


if __name__ == "__main__":
    app()
