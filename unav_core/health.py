"""Local health check: dependencies, config paths, sample data, DB and server.

Produces a structured report (and a human-readable rendering) so a developer can
see — in one command — whether the environment is ready: which packages are
installed (and which optional ones are missing, with install hints), where the
data lives, whether sample data and the database are present, and optionally
whether a server is reachable. Dependency-light; heavy/optional imports are lazy.

See ``docs/DEVELOPER_WORKFLOW.md``.
"""

from __future__ import annotations

import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from unav_core.config import Config, load_config

#: Required core packages and the optional stacks, with an install hint each.
_CORE_PACKAGES = ("astropy", "numpy", "pydantic", "sqlalchemy", "typer", "rich")
_OPTIONAL_HINTS: dict[str, str] = {
    "astroquery": 'real catalog/Horizons fetches — pip install -e ".[query]"',
    "pyvo": 'Virtual Observatory access — pip install -e ".[query]"',
    "fastapi": 'the local API server — pip install -e ".[server]"',
    "uvicorn": 'the local API server — pip install -e ".[server]"',
}


def _pkg_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def _count_jsonl_objects(path: Path) -> int | None:
    try:
        with path.open(encoding="utf-8") as handle:
            return sum(1 for line in handle if line.strip())
    except OSError:
        return None


def _db_object_count(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        from unav_core.db import Database

        db = Database(path)
        try:
            return db.count_objects()
        finally:
            db.dispose()
    except Exception:  # noqa: BLE001 - a broken/locked DB should not crash the check
        return None


def _probe_server(url: str) -> dict[str, Any]:
    import json
    import urllib.error
    import urllib.request

    try:
        with urllib.request.urlopen(url.rstrip("/") + "/health", timeout=1.0) as response:
            data = json.loads(response.read().decode("utf-8"))
        return {"status": "ok", "object_count": data.get("object_count")}
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return {"status": "unreachable", "detail": str(exc)}


def health_report(config: Config | None = None, *, check_server: bool = False) -> dict[str, Any]:
    """Build the structured health report (see :func:`render_health` to print it)."""
    config = config or load_config()
    packages = {name: _pkg_version(name) for name in (*_CORE_PACKAGES, *_OPTIONAL_HINTS)}

    sample = config.sample_catalog_path
    sample_exists = sample.exists()
    db_path = config.database_path

    return {
        "python": sys.version.split()[0],
        "core_ok": all(packages[name] for name in _CORE_PACKAGES),
        "packages": packages,
        "optional": {
            "query (astroquery)": packages["astroquery"] is not None,
            "vo (pyvo)": packages["pyvo"] is not None,
            "server (fastapi+uvicorn)": bool(packages["fastapi"] and packages["uvicorn"]),
        },
        "config": config.as_dict(),
        "sample_data": {
            "path": str(sample),
            "exists": sample_exists,
            "objects": _count_jsonl_objects(sample) if sample_exists else None,
        },
        "database": {
            "path": str(db_path),
            "exists": db_path.exists(),
            "object_count": _db_object_count(db_path),
        },
        "server": (
            {"url": config.server_url, **_probe_server(config.server_url)}
            if check_server
            else {"url": config.server_url, "status": "not checked"}
        ),
    }


def render_health(report: dict[str, Any]) -> str:
    """Render a report as a readable, multi-line string (no rich dependency)."""
    ok = "✓"
    bad = "✗"
    lines: list[str] = ["UNAV-SA health check", "=" * 21, f"python: {report['python']}"]

    lines.append("")
    lines.append("core dependencies:")
    pkgs = report["packages"]
    for name in _CORE_PACKAGES:
        v = pkgs.get(name)
        lines.append(f"  {ok if v else bad} {name}: {v or 'NOT INSTALLED'}")
    lines.append(f"  -> core {'ready' if report['core_ok'] else 'INCOMPLETE'}")

    lines.append("")
    lines.append("optional packages:")
    for name, hint in _OPTIONAL_HINTS.items():
        v = pkgs.get(name)
        if v:
            lines.append(f"  {ok} {name}: {v}")
        else:
            lines.append(f"  - {name}: not installed ({hint})")

    cfg = report["config"]
    lines += [
        "",
        "configuration (override with UNAV_* env vars):",
        f"  data dir:    {cfg['data_dir']}",
        f"  database:    {cfg['database_path']}",
        f"  cache dir:   {cfg['cache_dir']}",
        f"  server:      {cfg['server_host']}:{cfg['server_port']}",
        f"  query caps:  limit={cfg['default_query_limit']}, "
        f"max_radius={cfg['default_max_radius_deg']} deg",
    ]

    sample = report["sample_data"]
    db = report["database"]
    server = report["server"]
    lines += [
        "",
        "data:",
        f"  {ok if sample['exists'] else '-'} sample catalog: "
        + (
            f"{sample['objects']} objects ({sample['path']})"
            if sample["exists"]
            else f"missing ({sample['path']}) — generate with scripts/setup_dev.py"
        ),
        f"  {ok if db['exists'] else '-'} database: "
        + (
            f"{db['object_count']} objects ({db['path']})"
            if db["exists"]
            else f"not created ({db['path']}) — run scripts/run_demo.py"
        ),
        "",
        f"server: {server['status']} ({server['url']})",
    ]
    return "\n".join(lines)
