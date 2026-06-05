# UNAV-SA — Extragalactic Data Limitations

An honest account of what UNAV-SA does and does **not** claim when handling
extragalactic data (SDSS, DESI, and similar). The goal is to never produce
confident-looking bad science.

## 1. We do not mirror archives

UNAV-SA fetches **regional, limited** data and keeps a bounded local cache. It
never downloads complete surveys. For DESI specifically, region *downloading* is
not enabled at all — you import a file you already have, or (in future) issue a
small, capped query against a public service. See
[`DATA_FETCHING_SAFETY.md`](DATA_FETCHING_SAFETY.md) and
[`DESI_CONNECTOR.md`](DESI_CONNECTOR.md).

## 2. `z` is overloaded — redshift vs band magnitude

SDSS uses the column name **`z`** for the **redshift** (spectroscopic) *and* for
the **z-band magnitude** (photometric). These are unrelated quantities. UNAV-SA
only treats `z` as a redshift in spectroscopic mode (`spectro=True`); a
photometric `z` is never recorded as a redshift. Conflating them would assign
galaxies absurd distances.

## 3. Redshift is not distance

The connectors store **redshift** (`redshift`), not a derived `distance_pc`, for
extragalactic objects. Converting `z` to a distance is **not** a fixed factor:

- It requires a **cosmological model** (H₀, Ωm, ΩΛ) and a choice of distance
  (comoving, luminosity, angular-diameter) — these differ substantially.
- At low `z`, **peculiar velocities** dominate and redshift is a poor distance
  proxy; a small or negative `z` can be real (e.g. M31 is blueshifted).
- **Photometric** redshifts carry large uncertainties versus spectroscopic ones.

UNAV-SA deliberately keeps `redshift` as the measured quantity and leaves any
cosmological distance conversion to an explicit, model-aware step (not part of
this foundation). The `x/y/z` enrichment path (parallax → parsecs) is for
**nearby** objects and is **not** applied to redshift-based objects.

## 4. Quality flags matter

DESI rows carry `ZWARN` (0 = good); SDSS carries class/subclass and warning
flags. UNAV-SA preserves these in `metadata` rather than silently dropping
flagged rows, so downstream code can filter deliberately. Per the
[validation strategy](PROVENANCE_AND_VALIDATION.md), questionable records are
reported, not silently coerced.

## 5. Classification is the survey's, not ours

`object_type` for SDSS/DESI comes directly from the survey's pipeline
classification (`class`/`SPECTYPE`): `GALAXY→galaxy`, `QSO→quasar`,
`STAR→star`, otherwise `unknown`. UNAV-SA does not re-classify objects.

## 6. Provenance everywhere

Every fetched or imported record carries a `Provenance` (source, catalog, the
exact query parameters or source file, and `retrieved_at`) so any extragalactic
view remains reproducible and auditable.
