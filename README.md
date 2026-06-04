# UNAV-SA

**UNAV-SA — a standalone, real-time astronomical data navigator.**

UNAV-SA is a standalone engine and application for exploring real astronomical
data in 2D/3D: querying catalogs, inspecting objects, planning routes/missions,
and navigating the sky and nearby space using authoritative data sources such as
**Gaia, SDSS, DESI, NASA/JPL, SIMBAD, VizieR and MAST**.

> This repository currently contains the **architecture and project
> foundation** only. Data fetching, the UI, and DCC adapters are intentionally
> **not implemented yet** (see [Roadmap](docs/ROADMAP.md)).

## What UNAV-SA is — and is not

- ✅ A **standalone astro-data navigation engine and application**.
- ❌ **Not** a Cinema 4D plugin.
- ❌ **Not** a render engine.
- ❌ **Not** bound to any DCC.

DCC integrations (Cinema 4D, Blender, Houdini, Unreal) are **future adapters** —
thin clients layered on top of the engine. Cinema 4D will be the *first* adapter,
but it is never the core. See [`docs/PRODUCT_IDENTITY.md`](docs/PRODUCT_IDENTITY.md).

## Architecture at a glance

```
adapters/        Cinema 4D · Blender · Houdini · Unreal   (future, thin clients)
   │  (interchange / local API)
unav_server/     local API · future WebSocket state sync · adapter comms
   │
unav_app/        standalone 2D/3D UI: search · inspect · navigate · routes/missions
   │
unav_core/       DCC-independent engine: astronomy + data + navigation logic
```

- **`unav_core`** owns *all* astronomy and data logic and is independent from any
  DCC. Astropy (and optionally astroquery/pyvo) live here.
- **`unav_app`** is the standalone application that *uses* the core.
- **`unav_server`** exposes the core over a local API for the app and adapters.
- **`adapters/`** are clients — they consume data, they do **not** own astronomy
  logic, and heavy scientific dependencies never enter a DCC plugin runtime.

Full details: [`docs/UNAV_SA_ARCHITECTURE.md`](docs/UNAV_SA_ARCHITECTURE.md).

## Repository layout

```
unav_core/      astro · data · connectors · db · navigation · routes · missions · export · provenance
unav_app/       desktop · viewport · ui
unav_server/    local API / adapter communication
adapters/       cinema4d · blender · houdini · unreal   (future)
tools/          developer & operational tooling
docs/           architecture & strategy documents
tests/          test suite
samples/        small, curated example data and configs
```

## Documentation

| Document | Purpose |
| --- | --- |
| [UNAV_SA_ARCHITECTURE.md](docs/UNAV_SA_ARCHITECTURE.md) | Layered architecture and component responsibilities |
| [PRODUCT_IDENTITY.md](docs/PRODUCT_IDENTITY.md) | What UNAV-SA is and is not |
| [DATA_SOURCE_STRATEGY.md](docs/DATA_SOURCE_STRATEGY.md) | Catalogs, regional queries, cache, provenance, validation |
| [DCC_ADAPTER_STRATEGY.md](docs/DCC_ADAPTER_STRATEGY.md) | How DCC adapters integrate as clients |
| [ROADMAP.md](docs/ROADMAP.md) | Phased plan |

## Getting started (development)

Requires Python **3.10+**.

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install the core in editable mode with dev tooling
pip install -e ".[dev]"

# Optional stacks
pip install -e ".[query]"    # catalog / Virtual Observatory access
pip install -e ".[server]"   # local API server

# Run the tests
pytest
```

## Project status

Pre-alpha. The current milestone establishes the project skeleton, the
core/app/server/adapters boundaries, and the documentation that fixes the
product identity. See the [Roadmap](docs/ROADMAP.md) for what comes next.

## License

License: **TBD**. To be decided before the first feature release; see the
[Roadmap](docs/ROADMAP.md).
