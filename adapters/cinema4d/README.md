# adapters/cinema4d/

Cinema 4D adapter for UNAV-SA — **planning only. No C4D code is implemented yet.**

This will be the **first** DCC adapter, built *after* the standalone core and app
are useful on their own. It is a **client**: it connects to the UNAV-SA local API
(or reads exported interchange files) and maps results into Cinema 4D scene
objects. It does **not** own astronomy logic and must **not** pull heavy
scientific dependencies into Cinema 4D's Python runtime.

> Reminder: UNAV-SA is **not** a Cinema 4D plugin. Cinema 4D is an adapter on top
> of the standalone engine. See
> [`../../docs/DCC_ADAPTER_STRATEGY.md`](../../docs/DCC_ADAPTER_STRATEGY.md) and
> [`../../docs/ADAPTER_COMMUNICATION_MODEL.md`](../../docs/ADAPTER_COMMUNICATION_MODEL.md).

## Structure

```
adapters/cinema4d/
  README.md      this file
  docs/          the plan, MVP scope, protocol and ownership rules
  plugin/        (placeholder) the C4D-side plugin — c4d SDK + stdlib only
  client/        (placeholder) the stdlib HTTP/JSON client to the UNAV server
```

`plugin/` and `client/` are **placeholders** (a README each) — no implementation
yet; they fix where code will go.

## Documents

| Doc | Contents |
| --- | --- |
| [`docs/C4D_ADAPTER_MVP.md`](docs/C4D_ADAPTER_MVP.md) | **The MVP**: scope, the can/must-not, the API slice, and the first workflow (connect → mission → camera rig → bake timeline). |
| [`docs/C4D_LOCAL_API_PROTOCOL.md`](docs/C4D_LOCAL_API_PROTOCOL.md) | The MVP wire protocol (camera + mission), endpoint by endpoint, incl. the camera-path derivation. |
| [`docs/C4D_DATA_OWNERSHIP_RULES.md`](docs/C4D_DATA_OWNERSHIP_RULES.md) | The boundary contract: who owns what; the hard must-not rules. |
| [`docs/C4D_ADAPTER_PLAN.md`](docs/C4D_ADAPTER_PLAN.md) | The fuller design: responsibilities, runtime constraints, coordinate/units mapping, phasing. |
| [`docs/C4D_API_CLIENT_PROTOCOL.md`](docs/C4D_API_CLIENT_PROTOCOL.md) | The full client protocol (render payload, file fallback, future WebSocket). |
| [`docs/C4D_WORKFLOW.md`](docs/C4D_WORKFLOW.md) | The end-to-end artist workflow inside Cinema 4D. |

New here? Start with **C4D_ADAPTER_MVP.md**.

## In one sentence (the MVP)

The first thin adapter **connects** to the local UNAV server, **pulls a mission's
camera path**, **builds a camera rig** and **bakes it to the C4D timeline** — and
can **push the C4D camera back** — using the `c4d` SDK + Python stdlib only, with
**no** astronomy, data fetching, database or heavy rendering inside Cinema 4D.
