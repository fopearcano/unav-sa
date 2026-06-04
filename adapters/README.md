# adapters/

DCC (Digital Content Creation) integrations for UNAV-SA. **Future work.**

Adapters are **thin clients** that consume UNAV-SA data and navigation state and
translate them into a host application's scene. They do **not** own astronomy
logic, and they must **not** pull heavy scientific dependencies (astropy,
astroquery, ...) into the host runtime. All astronomy and data logic stays in
[`unav_core`](../unav_core); adapters talk to it through interchange payloads
(`unav_core.export`) and/or the local API (`unav_server`).

See [`docs/DCC_ADAPTER_STRATEGY.md`](../docs/DCC_ADAPTER_STRATEGY.md).

## Planned adapters

| Adapter | Status | Order |
| --- | --- | --- |
| [`cinema4d/`](cinema4d) | Not implemented | **First** |
| [`blender/`](blender) | Not implemented | Later |
| [`houdini/`](houdini) | Not implemented | Later |
| [`unreal/`](unreal) | Not implemented | Later |

Nothing here is implemented yet — these directories document intent only.
