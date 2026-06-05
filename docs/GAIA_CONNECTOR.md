# UNAV-SA — Gaia Connector

`unav_core.connectors.gaia` fetches **Gaia DR3** stars in a small sky region and
normalises them into UNAV `CatalogObject` records.

> Requires the optional `astroquery` dependency (`pip install -e ".[query]"`)
> and network access. See [`DATA_FETCHING_SAFETY.md`](DATA_FETCHING_SAFETY.md).

## API

```python
from unav_core.connectors.gaia import fetch_gaia_region

stars = fetch_gaia_region(ra_deg, dec_deg, radius_deg, limit=500,
                          *, allow_large_radius=False)  # -> list[CatalogObject]
```

A regional, row-capped ADQL cone search against `gaiadr3.gaia_source`:

```sql
SELECT TOP {limit} source_id, ra, dec, parallax, phot_g_mean_mag, bp_rp,
       pmra, pmdec, radial_velocity
FROM gaiadr3.gaia_source
WHERE 1 = CONTAINS(POINT('ICRS', ra, dec),
                   CIRCLE('ICRS', {ra}, {dec}, {radius}))
```

- `radius_deg` is capped at **5°** (override with `allow_large_radius=True`).
- `limit` defaults to **500**; above **5000** a `UserWarning` is emitted.

## Field mapping

| Gaia column | `CatalogObject` field |
| --- | --- |
| `source_id` | `uid = "gaia:{source_id}"`, `metadata.gaia_source_id` |
| (fixed) | `source = "Gaia DR3"`, `object_type = star` |
| `source_id` | `name = "Gaia DR3 {source_id}"` |
| `ra`, `dec` | `ra_deg`, `dec_deg` (ICRS) |
| `parallax` | `parallax_mas` (kept raw; may be ≤ 0) |
| `parallax` | `distance_pc = 1000 / parallax` **only when parallax > 0** |
| `phot_g_mean_mag` | `apparent_magnitude` |
| `bp_rp` | `color_index` |
| `pmra`, `pmdec` | `proper_motion_ra_masyr`, `proper_motion_dec_masyr` |
| `radial_velocity` | `radial_velocity_kms` (often missing → `None`) |

Missing/masked/NaN cells become `None`. Provenance records `Gaia DR3`, table
`gaiadr3.gaia_source`, epoch `J2016.0`, and the exact query parameters.

`distance_pc` is derived from a **positive** parallax only (negative/zero Gaia
parallaxes yield no distance). Cartesian `x/y/z` are **not** computed here —
enrich on import (`--enrich`) to derive them. See
[`GAIA_WORKFLOW.md`](GAIA_WORKFLOW.md) for the full fetch → import → view flow.

## CLI

```bash
python tools/fetch_gaia_region.py --ra 56.75 --dec 24.12 --radius-deg 0.2 \
    --limit 500 --output data/catalogs/gaia_test.jsonl \
    [--db data/unav.db --dataset-name gaia_test]   # optional direct import
```

## Errors

`AstroqueryNotInstalledError`, `ConnectorNetworkError`, `EmptyResultError`,
`MalformedResponseError` — all subclasses of `ConnectorError`.
