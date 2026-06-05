# UNAV-SA — DESI Connector (conservative foundation)

`unav_core.connectors.desi` provides a **deliberately conservative** DESI
foundation. DESI redshift catalogs are large and are distributed as files and
through public services — **not** as a casual cone-search download API — so
UNAV-SA does **not** download or mirror DESI archives.

> See [`DATA_FETCHING_SAFETY.md`](DATA_FETCHING_SAFETY.md) and
> [`EXTRAGALACTIC_DATA_LIMITATIONS.md`](EXTRAGALACTIC_DATA_LIMITATIONS.md).

## What this foundation provides

| Function | Status | Purpose |
| --- | --- | --- |
| `normalize_desi_rows(rows, *, provenance)` | ✅ working | Map DESI rows → `CatalogObject`. |
| `load_desi_file(path, *, limit=None)` | ✅ working | Import a **local** DESI catalog file. |
| `fetch_desi_region(ra, dec, radius)` | ⛔ not enabled | Raises `ConnectorNotSupportedError` with guidance. |

## Local-file import (the working pathway)

Bring your own DESI redshift catalog (e.g. a `zpix`/`zall` FITS file you have
already downloaded) and import it locally — nothing is fetched:

```python
from unav_core.connectors.desi import load_desi_file
objs = load_desi_file("zall-pix-edr.fits")   # FITS / ECSV / CSV / VOTable
```

```bash
python tools/fetch_desi_region.py --input zall-pix-edr.fits --output data/desi.jsonl
```

## Field mapping

| DESI column | `CatalogObject` |
| --- | --- |
| `TARGETID` | `uid = "desi:{TARGETID}"`, `metadata.desi_targetid` |
| (fixed) | `source = "DESI"` |
| `SPECTYPE` | `object_type`: `GALAXY→galaxy`, `QSO→quasar`, `STAR→star`, else `unknown` |
| `TARGET_RA`, `TARGET_DEC` | `ra_deg`, `dec_deg` |
| `Z` | `redshift` |
| `SPECTYPE`, `ZWARN` | `metadata.spectype`, `metadata.zwarn` |

Column names are matched case-insensitively. Always check `ZWARN` (0 = good) and
treat redshift→distance with care (see the limitations doc).

## Planned public-database workflow (future)

`fetch_desi_region` is intentionally a placeholder. The intended future workflow
queries DESI's **public** services *regionally and with strict row caps*:

- **NOIRLab Astro Data Lab** TAP/ADQL (`datalab.noirlab.edu`) — a cone/box ADQL
  query against the DESI release tables, mirroring the Gaia connector pattern.
- **SPARCL** — for retrieving individual spectra by identifier.

These will reuse the same safety limits (`enforce_limit`, `enforce_radius`),
provenance and normalisation as the other connectors. Until then, region
fetching raises:

```python
fetch_desi_region(180.0, 10.0, 0.1)
# ConnectorNotSupportedError: Live DESI region fetching is intentionally not enabled ...
```

## Errors

`ConnectorNotSupportedError` (region fetch), `MalformedResponseError`,
`EmptyResultError`, and `FileNotFoundError` (missing local file) — connector
errors subclass `ConnectorError`.
