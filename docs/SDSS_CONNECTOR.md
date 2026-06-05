# UNAV-SA — SDSS Connector

`unav_core.connectors.sdss` runs a **regional** SDSS query via
`astroquery.sdss` and normalises the results into UNAV `CatalogObject` records.

> Requires the optional `astroquery` dependency (`pip install -e ".[query]"`)
> and network access. See [`DATA_FETCHING_SAFETY.md`](DATA_FETCHING_SAFETY.md)
> and [`EXTRAGALACTIC_DATA_LIMITATIONS.md`](EXTRAGALACTIC_DATA_LIMITATIONS.md).

## API

```python
from unav_core.connectors.sdss import fetch_sdss_region

objs = fetch_sdss_region(ra_deg, dec_deg, radius_deg=0.05, limit=500,
                         *, spectro=True, data_release=17,
                         allow_large_radius=False)  # -> list[CatalogObject]
```

A small cone (default ~3′) is queried with `SDSS.query_region(...)`; the result
is capped to `limit` rows locally. `radius_deg` is bounded by the shared 5° cap
(override with `allow_large_radius`).

`normalize_sdss_rows(rows, *, provenance, spectro=True)` normalises already-read
rows (used by the tests).

## ⚠️ Redshift vs the z-band magnitude

SDSS exposes a column literally named **`z`** in two very different meanings:

- **Spectroscopic** (`spectro=True`): `z` is the **redshift**.
- **Photometric** (`spectro=False`): `z` is the **z-band magnitude**.

UNAV-SA only reads `z` as a redshift when `spectro=True`. In photometric mode
`redshift` is left `None` — a band magnitude is **never** misinterpreted as a
cosmological redshift.

## Field mapping

| SDSS | `CatalogObject` |
| --- | --- |
| `specobjid` (else `objid`) | `uid = "sdss:{id}"`, `metadata.sdss_id` |
| (fixed) | `source = "SDSS"` |
| `class` (spectro) / `type` (photo) | `object_type`: `STAR→star`, `GALAXY→galaxy`, `QSO→quasar`, `3→galaxy`, `6→star`, else `unknown` |
| `ra`, `dec` | `ra_deg`, `dec_deg` |
| `z` *(spectro only)* | `redshift` |
| `modelMag_r` (or `petroMag_r`/`psfMag_r`/`r`) | `apparent_magnitude` |
| `class`, `subclass` | `metadata.sdss_class`, `metadata.sdss_subclass` |

Missing/masked/NaN cells become `None`. The connector captures the r-band
magnitude and class; full multi-band photometry is out of scope for this
foundation.

## CLI

```bash
python tools/fetch_sdss_region.py --ra 150.0 --dec 2.2 --radius 0.05 \
    --limit 500 --spectro --output data/sdss_region.jsonl
# --photo for a photometric query (positions + r-band magnitude only)
```

## Errors

`AstroqueryNotInstalledError`, `ConnectorNetworkError`, `EmptyResultError`,
`MalformedResponseError` — all subclasses of `ConnectorError`.
