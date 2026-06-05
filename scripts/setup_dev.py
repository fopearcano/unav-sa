#!/usr/bin/env python3
"""One-command developer setup for UNAV-SA.

Prepares a local working environment: creates the data/cache directories,
generates the sample catalog (if missing), prints a health check, and shows the
next steps. With ``--install`` it also installs the project in editable mode with
the dev + server (+ optional query) extras.

    python scripts/setup_dev.py            # prepare + health check + instructions
    python scripts/setup_dev.py --install  # also pip-install the dev extras

See ``docs/DEVELOPER_WORKFLOW.md``.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import typer  # noqa: E402
from rich.console import Console  # noqa: E402

from unav_core.config import apply_dotenv, load_config  # noqa: E402
from unav_core.data.sample_generator import write_sample_catalog  # noqa: E402
from unav_core.health import health_report, render_health  # noqa: E402

app = typer.Typer(add_completion=False, help=__doc__)
console = Console()

_NEXT_STEPS = """
next steps:
  - run the demo:    python scripts/run_demo.py        (then open the printed URL)
  - run the tests:   python scripts/run_tests.py
  - check health:    python scripts/healthcheck.py
  - fetch real data: python tools/fetch_gaia_region.py --help   (needs the [query] extra)
"""


@app.command()
def main(
    install: bool = typer.Option(False, "--install", help="pip install -e the dev/server extras."),
    extras: str = typer.Option("dev,server", "--extras", help="Extras to install with --install."),
    count: int = typer.Option(100, "--count", help="Sample objects to generate."),
    seed: int = typer.Option(42, "--seed", help="Sample RNG seed."),
) -> None:
    """Prepare local directories + sample data, then report health and next steps."""
    apply_dotenv(_REPO_ROOT)
    config = load_config()

    if install:
        spec = f".[{extras}]"
        console.print(f"[bold]installing[/bold] {spec} (editable)…")
        subprocess.run([sys.executable, "-m", "pip", "install", "-e", spec], check=True)

    config.ensure_dirs()
    console.print(f"[green]✓[/green] data dir: {config.data_dir}")
    console.print(f"[green]✓[/green] cache dir: {config.cache_dir}")

    sample = config.sample_catalog_path
    if sample.exists():
        console.print(f"[green]✓[/green] sample catalog present: {sample}")
    else:
        written = write_sample_catalog(sample, count, seed=seed)
        console.print(f"[green]✓[/green] generated {written} sample objects → {sample}")

    console.print()
    print(render_health(health_report(config)))
    console.print(_NEXT_STEPS)


if __name__ == "__main__":
    app()
