# adapters/cinema4d/plugin/

**Placeholder — not implemented yet.** The Cinema 4D **plugin** will live here: the
C4D-facing code that runs inside Cinema 4D's bundled Python.

Planned contents (see [`../docs/C4D_ADAPTER_MVP.md`](../docs/C4D_ADAPTER_MVP.md)):

- a C4D dialog/command plugin (host/port, **Connect**, mission picker, the action
  buttons);
- the scene operations: build the camera rig, bake mission keyframes, optional
  waypoint nulls;
- the coordinate→scene mapping (UNAV ICRS parsecs ⇄ C4D units; see
  [`../docs/C4D_ADAPTER_PLAN.md`](../docs/C4D_ADAPTER_PLAN.md#coordinate--units-mapping)).

Hard constraints (see
[`../docs/C4D_DATA_OWNERSHIP_RULES.md`](../docs/C4D_DATA_OWNERSHIP_RULES.md)):
**only** the `c4d` SDK and the Python standard library — no `numpy`, `pydantic`,
`requests`, `sqlalchemy`, `astroquery`, or any astronomy/DB logic. It talks to the
[`../client/`](../client/) HTTP/JSON client; the science stays in UNAV-SA.
