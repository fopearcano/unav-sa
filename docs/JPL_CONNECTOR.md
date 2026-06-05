# UNAV-SA — JPL Horizons Connector

`unav_core.connectors.jpl` fetches solar-system body ephemerides from **NASA/JPL
Horizons** and normalises them into UNAV `CatalogObject` records.

> Requires the optional `astroquery` dependency (`pip install -e ".[query]"`)
> and network access. See [`DATA_FETCHING_SAFETY.md`](DATA_FETCHING_SAFETY.md).

## API

```python
from unav_core.connectors.jpl import fetch_jpl_body, fetch_jpl_solar_system

mars = fetch_jpl_body("499", "2451545.0", center="@sun", object_type="planet")

bodies = fetch_jpl_solar_system(
    {"199": "planet", "299": "planet", "499": "planet"},
    epoch="2451545.0", center="@sun",
)  # -> list[CatalogObject]
```

- `body` — a Horizons id/name (e.g. `"Mars"` or `"499"`).
- `epoch` — a Julian Date (number or numeric string) or an ISO-8601 time
  (converted to JD via Astropy). It is part of the object's identity — see
  [`EPOCH_OBJECTS.md`](EPOCH_OBJECTS.md).
- `center` — a Horizons observer/location code (default `@sun`).
- `object_type` — `planet` / `moon` / `asteroid` / `comet` / `unknown`.
  `fetch_jpl_solar_system` accepts a `{name: type}` mapping or a sequence of
  names; bare names are classified by `classify_body` (well-known planets/moons),
  else `unknown`.

## Field mapping

| Horizons column | `CatalogObject` field |
| --- | --- |
| (fixed) | `uid = "jpl:{body}:{epoch}"`, `source = "JPL Horizons"` |
| name / `--type` | `object_type` (classified by name, e.g. `Mars` → planet) |
| `targetname` | `name` (falls back to `body`) |
| `RA`, `DEC` | `ra_deg`, `dec_deg` (ICRS, deg) |
| `delta` (AU) | `distance_pc` (AU→pc) + `metadata.distance_au` |
| (computed) | `x`, `y`, `z` — ICRS Cartesian (pc), enriched from ra/dec/distance |
| `V` | `apparent_magnitude` |

`metadata` also records `body`, `center` and `epoch`. Provenance records the
source, epoch and query parameters.

> Solar-system ranges are tiny in parsecs (1 AU ≈ 4.85e-6 pc); the AU value is
> kept in `metadata.distance_au` and the bodies cluster near the origin in a
> parsec-scale view (see [`EPOCH_OBJECTS.md`](EPOCH_OBJECTS.md)).

## CLI

```bash
# single body (type classified from the name)
python tools/fetch_jpl_body.py --body Mars --epoch 2026-01-01T00:00:00 \
    --center 500@10 --output data/catalogs/jpl_mars.jsonl

# several bodies, imported into the DB
python tools/fetch_jpl_solar_system.py --epoch 2026-01-01T00:00:00 \
    --bodies Mercury,Venus,Earth,Mars,Jupiter,Saturn,Uranus,Neptune,Pluto,Moon \
    --output data/catalogs/jpl_solar_system.jsonl \
    --db data/unav.db --dataset-name jpl_solar_system_2026
```

See [`JPL_SOLAR_SYSTEM_WORKFLOW.md`](JPL_SOLAR_SYSTEM_WORKFLOW.md) for the full
fetch → import → view flow.

## Errors

`AstroqueryNotInstalledError`, `ConnectorNetworkError`, `EmptyResultError`,
`MalformedResponseError` — all subclasses of `ConnectorError`.
