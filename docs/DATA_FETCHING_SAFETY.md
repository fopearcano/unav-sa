# UNAV-SA — Data Fetching Safety

How the connectors (`unav_core.connectors`) fetch **real** data **responsibly**.
This is the operational complement to
[`DATA_SOURCE_STRATEGY.md`](DATA_SOURCE_STRATEGY.md).

> Phase 5 scope: Gaia DR3 and NASA/JPL Horizons. SDSS/DESI/SIMBAD/VizieR/MAST are
> future work behind the same patterns.

## Principles

- **Regional & limited only.** No bulk downloads, no catalog mirroring. Every
  query is bounded (a small cone, a single body/epoch) and row-capped.
- **astroquery is optional and lazy.** Importing a connector never imports
  astroquery; it is pulled in only when a fetch runs. A missing install raises
  `AstroqueryNotInstalledError` with install instructions — it must never be
  required inside a DCC runtime.
- **Normalise + provenance.** Every fetched row becomes a validated
  `CatalogObject` carrying a `Provenance` record (source, catalog, epoch, the
  exact query parameters, and `retrieved_at`).

## Safety limits

| Control | Default | Behaviour |
| --- | --- | --- |
| Gaia row `limit` | **500** | Requested server-side via `SELECT TOP n`. |
| Hard-warn ceiling | **5000** | `limit > 5000` emits a loud `UserWarning`. |
| Cone `radius` cap | **5°** | A larger radius raises `ValueError` unless `allow_large_radius=True`. |

These live in `unav_core.connectors.base` (`enforce_limit`, `enforce_radius`).

## Error model

All connector errors derive from `ConnectorError`:

| Exception | Raised when |
| --- | --- |
| `AstroqueryNotInstalledError` | astroquery is not installed. |
| `ConnectorNetworkError` | the remote query/service call fails. |
| `EmptyResultError` | the query succeeds but returns no rows. |
| `MalformedResponseError` | the response can't be read or fails schema validation. |

`astroquery_available()` lets callers feature-detect before fetching.

## Distances & enrichment

Connectors map only the archive's raw fields (e.g. Gaia `parallax`, JPL
`delta`). They do **not** compute distances or Cartesian `x/y/z` — that is the
optional Astropy enrichment step, so the connectors themselves need no Astropy.
Pipe fetched JSONL through the importer with `--enrich` to populate `x/y/z` for
3D queries (see [`LOCAL_DATABASE.md`](LOCAL_DATABASE.md)).

## Responsible use

- Respect each archive's terms and rate limits; prefer small radii and the
  default row caps.
- Cache locally (`unav_core.db`) to avoid repeat traffic.
- Treat large pulls as an explicit, opt-in, offline operation — not part of
  interactive navigation.

## Testing

Connector tests use **mocked** astroquery responses (a fake `astroquery.*`
module returning Astropy tables) and **never touch the network**. See
`tests/test_gaia_connector.py` and `tests/test_jpl_connector.py`.
