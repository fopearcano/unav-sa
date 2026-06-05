# UNAV-SA — Epoch Objects (Static Positions)

Some bodies — Solar System planets, moons, asteroids, comets, spacecraft — have
no fixed catalog position: where they are depends on **when** you look. UNAV-SA
represents them as **epoch objects**: a position *snapshot* at one instant, not a
trajectory.

> Produced by the JPL Horizons connector (see
> [`JPL_SOLAR_SYSTEM_WORKFLOW.md`](JPL_SOLAR_SYSTEM_WORKFLOW.md)). The same idea
> applies to any time-dependent body.

## A snapshot, not a trajectory

An epoch object is one `CatalogObject` holding the body's position **at a single
epoch**. UNAV-SA does **not** propagate orbits or animate motion in this phase —
it stores what Horizons reported for that instant.

- The **epoch is part of the identity**: `uid = "jpl:{body}:{epoch}"`. Fetching
  Mars at two epochs yields two distinct objects
  (`jpl:Mars:2026-01-01T00:00:00`, `jpl:Mars:2026-07-01T00:00:00`) that coexist
  in the database — a small time series of snapshots, not an overwrite.
- The epoch is recorded in `metadata.epoch` **and** `provenance.epoch`, so the
  inspector always shows *when* the position is valid.

## Center matters

A Solar System position is **relative to a center** (origin/observer). The center
is part of the query and is recorded in `metadata.center` (e.g. `@sun` for
heliocentric, `500@10`, a planet code, …). Two fetches of the same body at the
same epoch but different centers describe different geometry; both are kept and
labelled.

## Scale: AU stored as parsecs

UNAV-SA's Cartesian `x/y/z` are **parsecs** everywhere (one unit convention, so
stars and planets share a frame). Solar System distances are **AU-scale**
(`1 AU ≈ 4.85 × 10⁻⁶ pc`), so an epoch object's `x/y/z` are *tiny* numbers near
the origin.

Consequences:

- In a **galactic** (parsec-scale) view mixed with stars, planets collapse onto
  the origin — expected, given the 10⁵–10⁶× scale gap.
- In a **JPL-only** dataset, the 3D viewport auto-frames to the bodies' extent,
  so the Solar System lays out correctly at its own scale. `distance_au` is kept
  in `metadata` for reference.

This is the honest trade-off of a single shared length unit. A future "scene
scale" per dataset could rescale epoch objects for display; the stored data stays
in true parsecs.

## Why not animate?

Real-time propagation (Kepler/SPICE) and timeline scrubbing are deliberately out
of scope for the foundation: they add an ephemeris engine and a time model that
the navigator does not yet need. Snapshots are enough to **place** Solar System
bodies in the navigator and inspect them, and they compose cleanly with the rest
of the catalog. Animation can layer on later by fetching a sequence of epochs.

## Summary

| Property | Epoch object |
| --- | --- |
| Identity | `uid = source:body:epoch` (epoch-specific) |
| Position | snapshot at one epoch (no propagation) |
| Center | recorded in `metadata.center` |
| Units | `x/y/z` in parsecs (AU-scale → tiny); `distance_au` in metadata |
| Provenance | epoch + center + query params + retrieval time |
