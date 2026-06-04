"""Smoke tests: the three top-level UNAV-SA packages must import cleanly.

These tests intentionally avoid importing heavy scientific dependencies
(astropy, numpy, ...). The top-level packages keep their ``__init__`` modules
side-effect free, so importing them must succeed even in a minimal environment.
This guards the architectural rule that ``import unav_*`` stays cheap and
runtime/DCC friendly.
"""

import importlib

import pytest

TOP_LEVEL_PACKAGES = ["unav_core", "unav_app", "unav_server"]


@pytest.mark.parametrize("module_name", TOP_LEVEL_PACKAGES)
def test_package_imports(module_name: str) -> None:
    module = importlib.import_module(module_name)
    assert module is not None
    assert module.__name__ == module_name


def test_core_exposes_version() -> None:
    import unav_core

    assert isinstance(unav_core.__version__, str)
    assert unav_core.__version__
