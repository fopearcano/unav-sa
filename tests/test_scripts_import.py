"""The one-command scripts must import cleanly and expose a Typer ``app``."""

import importlib.util
from pathlib import Path

import pytest
import typer

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = ["setup_dev", "run_demo", "run_server", "run_tests", "healthcheck"]


@pytest.mark.parametrize("name", _SCRIPTS)
def test_script_imports_and_has_app(name: str) -> None:
    path = _REPO_ROOT / "scripts" / f"{name}.py"
    assert path.is_file(), f"missing scripts/{name}.py"
    spec = importlib.util.spec_from_file_location(f"unav_script_{name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # importing must not error or start anything
    assert isinstance(module.app, typer.Typer)
