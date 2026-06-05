"""Local configuration: paths, query caps and server defaults (env-overridable).

A small, dependency-light settings object resolved from environment variables
(prefixed ``UNAV_``) over sensible project-relative defaults. Importing this
module pulls in nothing heavy (stdlib only), so it is safe to read config early
and everywhere. See ``docs/LOCAL_CONFIGURATION.md``.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

#: Environment-variable prefix for every setting.
ENV_PREFIX = "UNAV_"

#: Repository / project root (this file lives at ``<root>/unav_core/config.py``).
PROJECT_ROOT = Path(__file__).resolve().parent.parent

#: Defaults (mirrors ``unav_core.connectors.base`` for the query caps).
DEFAULT_QUERY_LIMIT = 500
DEFAULT_MAX_RADIUS_DEG = 5.0
DEFAULT_SERVER_HOST = "127.0.0.1"
DEFAULT_SERVER_PORT = 8765
SAMPLE_CATALOG_NAME = "sample_catalog.jsonl"


@dataclass(frozen=True)
class Config:
    """Resolved local configuration (paths, caps, server defaults)."""

    data_dir: Path
    database_path: Path
    cache_dir: Path
    samples_dir: Path
    default_query_limit: int
    default_max_radius_deg: float
    server_host: str
    server_port: int

    @property
    def sample_catalog_path(self) -> Path:
        """Path to the bundled sample catalog JSONL."""
        return self.samples_dir / SAMPLE_CATALOG_NAME

    @property
    def server_url(self) -> str:
        return f"http://{self.server_host}:{self.server_port}/"

    def as_dict(self) -> dict[str, object]:
        """A JSON-friendly view (paths as strings) for health/diagnostics."""
        return {
            "data_dir": str(self.data_dir),
            "database_path": str(self.database_path),
            "cache_dir": str(self.cache_dir),
            "samples_dir": str(self.samples_dir),
            "default_query_limit": self.default_query_limit,
            "default_max_radius_deg": self.default_max_radius_deg,
            "server_host": self.server_host,
            "server_port": self.server_port,
        }

    def ensure_dirs(self) -> None:
        """Create the data and cache directories if they do not exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)


def load_config(*, env: Mapping[str, str] | None = None, root: Path | None = None) -> Config:
    """Resolve :class:`Config` from ``env`` (default ``os.environ``) over defaults.

    Recognised variables (all optional): ``UNAV_DATA_DIR``, ``UNAV_DB_PATH``,
    ``UNAV_CACHE_DIR``, ``UNAV_SAMPLES_DIR``, ``UNAV_QUERY_LIMIT``,
    ``UNAV_MAX_RADIUS_DEG``, ``UNAV_SERVER_HOST``, ``UNAV_SERVER_PORT``.
    """
    env = os.environ if env is None else env
    root = (root or PROJECT_ROOT).resolve()

    def get(name: str, default: str) -> str:
        return env.get(ENV_PREFIX + name, default)

    data_dir = Path(get("DATA_DIR", str(root / "data"))).expanduser()
    cache_dir = Path(get("CACHE_DIR", str(data_dir / "cache"))).expanduser()
    samples_dir = Path(get("SAMPLES_DIR", str(root / "samples"))).expanduser()
    database_path = Path(get("DB_PATH", str(data_dir / "unav.db"))).expanduser()

    return Config(
        data_dir=data_dir,
        database_path=database_path,
        cache_dir=cache_dir,
        samples_dir=samples_dir,
        default_query_limit=int(get("QUERY_LIMIT", str(DEFAULT_QUERY_LIMIT))),
        default_max_radius_deg=float(get("MAX_RADIUS_DEG", str(DEFAULT_MAX_RADIUS_DEG))),
        server_host=get("SERVER_HOST", DEFAULT_SERVER_HOST),
        server_port=int(get("SERVER_PORT", str(DEFAULT_SERVER_PORT))),
    )


def parse_dotenv(text: str) -> dict[str, str]:
    """Parse ``KEY=VALUE`` lines from a ``.env`` body (ignoring blanks/comments)."""
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def apply_dotenv(root: Path | None = None) -> dict[str, str]:
    """Load ``<root>/.env`` into ``os.environ`` (without overriding existing vars).

    Returns the values that were applied. A missing ``.env`` is a no-op.
    """
    root = root or PROJECT_ROOT
    env_file = root / ".env"
    if not env_file.is_file():
        return {}
    applied: dict[str, str] = {}
    for key, value in parse_dotenv(env_file.read_text(encoding="utf-8")).items():
        if key not in os.environ:
            os.environ[key] = value
            applied[key] = value
    return applied
