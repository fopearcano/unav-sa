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

- `body` — a Horizons id/name (e.g. `"499"` = Mars).
- `epoch` — a Julian Date (number or numeric string) or an ISO-8601 time
  (converted to JD via Astropy).
- `center` — a Horizons observer/location code (default `@sun`).
- `object_type` — `planet` / `moon` / `asteroid` / `comet` / `unknown`.
  `fetch_jpl_solar_system` accepts a sequence of names (typed `unknown`) or a
  `{name: type}` mapping.

## Field mapping

| Horizons column | `CatalogObject` field |
| --- | --- |
| (fixed) | `uid = "jpl:{body}:{epoch}"`, `source = "JPL Horizons"` |
| caller | `object_type` |
| `targetname` | `name` (falls back to `body`) |
| `RA`, `DEC` | `ra_deg`, `dec_deg` (ICRS, deg) |
| `delta` (AU) | `distance_pc` (AU→pc) + `metadata.distance_au` |
| `V` | `apparent_magnitude` |

`metadata` also records `body`, `center` and `epoch`. Provenance records the
source, epoch and query parameters.

> Solar-system ranges are tiny in parsecs (1 AU ≈ 4.85e-6 pc); the AU value is
> kept in `metadata.distance_au` for readability.

## CLI

```bash
# single body
python tools/fetch_jpl_body.py --body 499 --epoch 2451545.0 \
    --center @sun --type planet --output data/mars.jsonl

# several bodies
python tools/fetch_jpl_solar_system.py \
    --bodies "199=planet,299=planet,499=planet" \
    --epoch 2451545.0 --center @sun --output data/planets.jsonl
```

## Errors

`AstroqueryNotInstalledError`, `ConnectorNetworkError`, `EmptyResultError`,
`MalformedResponseError` — all subclasses of `ConnectorError`.
