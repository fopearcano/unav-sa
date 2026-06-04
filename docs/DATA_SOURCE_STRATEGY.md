# UNAV-SA — Data Source Strategy

How UNAV-SA accesses real astronomical data **responsibly**: regional queries,
local cache, provenance and validation — never bulk catalog downloads.

## Goals

- Use **real, authoritative** data sources.
- Query **regions**, not whole surveys.
- Keep a **bounded local cache** for real-time, offline-friendly navigation.
- Attach **provenance** to everything and **validate** every record.
- Normalise heterogeneous sources into one **canonical schema**.

## Target data sources

| Source | Domain | Typical access | Notes |
| --- | --- | --- | --- |
| **Gaia** | Astrometry, stars (positions, parallax, proper motion, photometry) | TAP/ADQL (Gaia archive), astroquery | Primary source for stellar 3D positions. |
| **SDSS** | Imaging & spectra, galaxies/quasars | TAP/SQL, astroquery | Wide-area extragalactic + stellar. |
| **DESI** | Spectroscopy, redshifts (large-scale structure) | TAP / data releases | Redshift-based distances for galaxies. |
| **NASA/JPL** | Solar-system bodies, ephemerides | Horizons API | Time-dependent positions of planets/minor bodies. |
| **SIMBAD** | Object identifiers, basic data, cross-IDs | astroquery.simbad | Name/identifier resolution and metadata. |
| **VizieR** | Hosted catalogs (thousands) | astroquery.vizier / TAP | Access to specific published catalogs. |
| **MAST** | Mission archives (HST, JWST, TESS, ...) | astroquery.mast / VO | Observations and products. |

Access libraries (**optional** extras, imported lazily): `astroquery`, `pyvo`.
Astropy is always available in the core for coordinates/time/units and table
handling.

## Regional query principle

UNAV-SA issues **bounded** queries tied to the region the user is navigating:

- **Cone search** — center (RA/Dec) + radius.
- **Box / footprint** — a bounded sky region.
- **Volume** — a region plus a distance/parallax (or redshift) range.
- **Result caps** — every query carries a row limit and a sane default radius.

> **Do not** attempt to download complete huge catalogs by default. Bulk pulls,
> if ever needed, are an explicit, opt-in, offline operation — not part of
> interactive navigation.

## Local cache

- A **bounded working set** of records relevant to the current/recent regions,
  stored locally via `unav_core.db` (SQLAlchemy over a SQLite baseline).
- Backed by a **spatial index** so cached regions answer cone/box/volume
  queries without re-hitting the network.
- Cache entries are keyed by region + query parameters and carry provenance and
  expiry, so stale data can be refreshed deliberately.
- The cache is **never** a full survey mirror.

## Provenance

Every record and result set carries provenance (`unav_core.provenance`):

- **source** — which service (Gaia, SDSS, ...).
- **query** — the exact parameters (region, filters, row limit, ADQL/endpoint).
- **catalog / data release & version** — e.g. Gaia DR3.
- **retrieved_at** — timestamp of retrieval.
- **assumptions** — reference frame, epoch, units.

This makes any view, route or mission **reproducible and auditable**.

## Validation

- Incoming rows are normalised and **validated** against the canonical
  `unav_core.data` schema (pydantic): required fields, types, units, coordinate
  ranges and frame consistency.
- Records that fail validation are rejected or quarantined with a reason —
  never silently coerced into navigation.
- Units and frames are reconciled against the canonical `unav_core.astro`
  registry so all sources end up consistent.

## Responsible access

- Respect each archive's terms, rate limits and recommended endpoints.
- Prefer standard **Virtual Observatory** protocols (TAP/ADQL, cone search)
  where available.
- Default to small radii and row limits; make the user opt in to larger pulls.
- Cache to **minimise** repeat traffic.

## Status

No connectors or fetching logic are implemented in this milestone. This document
defines the strategy the `unav_core.connectors`, `unav_core.db` and
`unav_core.provenance` packages are scaffolded to implement. See
[`ROADMAP.md`](ROADMAP.md).
