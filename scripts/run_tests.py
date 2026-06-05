#!/usr/bin/env python3
"""Run the UNAV-SA test suite (and optionally ruff lint/format checks).

A one-command wrapper around ``pytest``; extra arguments are forwarded to it.

    python scripts/run_tests.py                 # run the suite
    python scripts/run_tests.py --lint          # also run ruff check + format --check
    python scripts/run_tests.py -- -k voyage     # forward args to pytest

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

app = typer.Typer(add_completion=False, help=__doc__, context_settings={"allow_extra_args": True})
console = Console()


def _run(label: str, command: list[str]) -> int:
    console.print(f"[bold]$ {' '.join(command)}[/bold]")
    return subprocess.run(command, cwd=_REPO_ROOT).returncode


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def main(
    ctx: typer.Context,
    lint: bool = typer.Option(False, "--lint", help="Also run ruff check + format --check."),
) -> None:
    """Run ruff (optional) then pytest; exit non-zero on the first failure."""
    if lint:
        code = _run("ruff check", [sys.executable, "-m", "ruff", "check", "."])
        if code == 0:
            code = _run("ruff format", [sys.executable, "-m", "ruff", "format", "--check", "."])
        if code != 0:
            raise typer.Exit(code=code)

    pytest_cmd = [sys.executable, "-m", "pytest", *ctx.args]
    raise typer.Exit(code=_run("pytest", pytest_cmd))


if __name__ == "__main__":
    app()
