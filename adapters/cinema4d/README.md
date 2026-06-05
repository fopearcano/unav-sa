# adapters/cinema4d/

Cinema 4D adapter for UNAV-SA — **planning only. Not implemented yet** (Phase 13
is design; no C4D code is written here).

This will be the **first** DCC adapter, built *after* the standalone core and app
are useful on their own. It is a **client**: it connects to the UNAV-SA local API
(or reads exported interchange files) and maps results into Cinema 4D scene
objects. It does **not** own astronomy logic and must **not** pull heavy
scientific dependencies into Cinema 4D's Python runtime.

> Reminder: UNAV-SA is **not** a Cinema 4D plugin. Cinema 4D is an adapter on top
> of the standalone engine. See
> [`../../docs/DCC_ADAPTER_STRATEGY.md`](../../docs/DCC_ADAPTER_STRATEGY.md) and
> [`../../docs/ADAPTER_COMMUNICATION_MODEL.md`](../../docs/ADAPTER_COMMUNICATION_MODEL.md).

## Planning documents

| Doc | Contents |
| --- | --- |
| [`docs/C4D_ADAPTER_PLAN.md`](docs/C4D_ADAPTER_PLAN.md) | Responsibilities, hard "must-not" rules, runtime constraints, architecture, coordinate/units mapping, phasing. |
| [`docs/C4D_API_CLIENT_PROTOCOL.md`](docs/C4D_API_CLIENT_PROTOCOL.md) | How the adapter talks to UNAV: HTTP local API (first), file-export fallback, future WebSocket; endpoint→action map; payloads; errors. |
| [`docs/C4D_WORKFLOW.md`](docs/C4D_WORKFLOW.md) | The end-to-end artist workflow inside Cinema 4D. |

## In one sentence

The adapter pulls a **navigator state**, a **visible-sector render payload**, and
**routes/missions** from UNAV over a thin localhost HTTP boundary (stdlib only,
no astropy/numpy/db), builds a **camera/null rig** and a **lightweight point**
representation, **bakes missions** to the C4D timeline, and can **push the C4D
camera back** to UNAV — nothing more.
