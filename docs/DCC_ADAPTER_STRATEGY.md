# UNAV-SA — DCC Adapter Strategy

How Digital Content Creation (DCC) tools integrate with UNAV-SA. The guiding
rule is simple:

> **Adapters are clients, not owners of astronomy logic.**

## Principles

1. **The core is independent.** `unav_core` never imports or depends on any DCC.
2. **Adapters consume, they don't compute.** An adapter receives data and
   navigation state from UNAV-SA and translates it into its host's scene. It
   does not perform coordinate math, catalog queries, validation or provenance —
   all of that lives in the core.
3. **No heavy science in host runtimes.** DCC plugin runtimes are fragile,
   version-locked Python environments. Adapters must **not** require astropy,
   numpy-heavy stacks, astroquery, etc. inside the host. They talk to UNAV-SA
   over a thin boundary instead.
4. **One source of truth.** Because every adapter reads the same exported
   interchange / local API, all hosts show identical, correct data.

## Integration boundary

Adapters attach via the **standalone** side, never by embedding the core:

```
unav_core ── unav_server (local API) ──┐
        └── export / interchange ──────┤→  adapter (inside DCC)  →  host scene
                                        │   thin client, no science deps
```

Two complementary mechanisms:

- **Interchange payloads** (`unav_core.export`) — portable, serialised
  objects/regions/routes/missions/navigation state an adapter can import.
- **Local API** (`unav_server`) — request data and (future) subscribe to
  real-time navigation **state sync** over WebSocket.

An adapter is therefore a small package that: (a) speaks the UNAV interchange /
API, and (b) maps results into host objects (nulls/points/cameras/splines/etc.).

## Roll-out order

1. **Cinema 4D — first.** The first adapter to be built, *after* the core and
   the standalone app are useful on their own. Still just a client.
2. **Blender, Houdini, Unreal — later.** Added incrementally against the same
   boundary, reusing the same interchange/API.

## What belongs where

| Concern | Core / App / Server | Adapter |
| --- | --- | --- |
| Coordinates, time, units | ✅ | ❌ |
| Catalog queries & connectors | ✅ | ❌ |
| Validation & provenance | ✅ | ❌ |
| Navigation state | ✅ (authoritative) | reflects it |
| Routes / missions | ✅ | reads/triggers |
| Heavy dependencies (astropy, ...) | ✅ | ❌ never |
| Host scene objects (nulls, cameras, splines) | ❌ | ✅ |
| Host-specific UI/handles | ❌ | ✅ |

## Why not a DCC plugin as the core?

Putting astronomy inside a DCC plugin would trap heavy scientific dependencies
in a fragile runtime, duplicate logic per host, and tie the product's lifetime
to one application. Keeping UNAV-SA standalone and treating DCCs as adapters
avoids all three. See [`PRODUCT_IDENTITY.md`](PRODUCT_IDENTITY.md).

## Status

No adapter is implemented in this milestone. The `adapters/` directory holds
placeholders that document intent only. The Cinema 4D adapter comes *after* the
standalone core and app — see [`ROADMAP.md`](ROADMAP.md).
