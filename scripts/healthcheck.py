#!/usr/bin/env python3
"""One-command environment health check for UNAV-SA.

Reports Python + dependency versions (and which optional packages are missing,
with install hints), the resolved configuration paths, sample-data and database
availability, and — with ``--server`` — whether the local server is reachable.

    python scripts/healthcheck.py
    python scripts/healthcheck.py --server   # also probe the configured server

See ``docs/DEVELOPER_WORKFLOW.md``.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import typer  # noqa: E402

from unav_core.config import apply_dotenv, load_config  # noqa: E402
from unav_core.health import health_report, render_health  # noqa: E402

app = typer.Typer(add_completion=False, help=__doc__)


@app.command()
def main(
    server: bool = typer.Option(False, "--server", help="Also probe the configured server URL."),
) -> None:
    """Print the health report; exit non-zero if core dependencies are missing."""
    apply_dotenv(_REPO_ROOT)
    report = health_report(load_config(), check_server=server)
    print(render_health(report))
    raise typer.Exit(code=0 if report["core_ok"] else 1)


if __name__ == "__main__":
    app()
