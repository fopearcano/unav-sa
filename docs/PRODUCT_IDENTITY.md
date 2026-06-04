# UNAV-SA — Product Identity

This document fixes **what UNAV-SA is and is not**. It is the reference every
other design decision must stay consistent with.

## One-line definition

> **UNAV-SA is a standalone astro-data navigation engine and application.**
> DCC integrations are thin adapters layered on top — never the core.

## What UNAV-SA is

UNAV-SA is a **standalone, real-time astronomical data navigator**: an engine
and an application for exploring real astronomical data in 2D and 3D. It lets a
user search authoritative catalogs, inspect objects, plan routes and missions,
and navigate the sky and nearby space using real data sources such as **Gaia,
SDSS, DESI, NASA/JPL, SIMBAD, VizieR and MAST**.

It runs on its own. It does not need any host application to function.

## What UNAV-SA is NOT

- **NOT a Cinema 4D plugin.** Cinema 4D is a *future adapter*, not the product.
- **NOT a render engine.** UNAV-SA owns *data and navigation*, not rendering.
  A viewport presents navigation state; it is not the reason the system exists.
- **NOT bound to any DCC.** Blender, Houdini, Unreal and Cinema 4D are
  downstream *clients*.
- **NOT a bulk catalog mirror.** It does not download entire surveys by default;
  it performs bounded, regional queries and keeps a small local working set.

## Why the boundary matters

1. **Dependency isolation.** Astronomy needs heavy scientific libraries
   (astropy, numpy, and optionally astroquery/pyvo). DCC plugin runtimes are
   fragile, version-locked Python environments. Keeping all science in
   `unav_core` (and the standalone app/server) means those heavy dependencies
   **never** have to be installed inside Cinema 4D, Blender, Houdini or Unreal.

2. **Single source of truth.** Coordinates, time, units, schema, provenance and
   validation are defined once, in the core. Adapters cannot drift or
   re-implement astronomy logic, so every host shows the same, correct data.

3. **Longevity.** Hosts come and go and break compatibility. A standalone core
   outlives any individual DCC and can grow new adapters without being rewritten.

## Product pillars

- **Real data, with provenance.** Every object carries where it came from,
  which query produced it, and when — so any view is reproducible and auditable.
- **Regional, real-time navigation.** Bounded spatial queries and a local cache
  keep interaction fast and offline-friendly.
- **Validated and typed.** A canonical, validated schema normalises records from
  many heterogeneous sources into one consistent model.
- **Standalone first, adapters later.** The standalone app is the primary
  product surface; DCC adapters are additive.

## Layering (identity in one picture)

```
adapters/      Cinema 4D · Blender · Houdini · Unreal   (future, thin clients)
   ▲  consume interchange / call the local API; own NO astronomy logic
unav_server/   local API · future WebSocket state sync · adapter comms
   ▲
unav_app/      standalone 2D/3D UI (search · inspect · navigate · routes/missions)
   ▲
unav_core/     DCC-independent engine: ALL astronomy + data + navigation logic
```

See [`UNAV_SA_ARCHITECTURE.md`](UNAV_SA_ARCHITECTURE.md) for the full breakdown
and [`DCC_ADAPTER_STRATEGY.md`](DCC_ADAPTER_STRATEGY.md) for how adapters attach.
