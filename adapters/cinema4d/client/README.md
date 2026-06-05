# adapters/cinema4d/client/

**Placeholder — not implemented yet.** The thin **HTTP/JSON client** to the UNAV-SA
local server will live here — the only thing the plugin uses to reach UNAV.

Planned contents (see
[`../docs/C4D_LOCAL_API_PROTOCOL.md`](../docs/C4D_LOCAL_API_PROTOCOL.md)):

- an `api_client` using **stdlib only** (`urllib.request`, `json`): base URL,
  timeouts, retries;
- typed-ish wrappers for the MVP endpoints: `health()`, `get_navigator_state()`,
  `post_navigator_state()`, `list_routes()`, `list_missions()`, `get_mission(id)`,
  and the derived **camera path** (from the mission segments);
- a JSON **file-fallback** reader (same serialised models) for offline handoff.

Hard constraints (see
[`../docs/C4D_DATA_OWNERSHIP_RULES.md`](../docs/C4D_DATA_OWNERSHIP_RULES.md)): **no**
heavy dependencies (`requests`, `numpy`, `pydantic`, …) so it runs inside Cinema
4D's bundled Python. The HTTP/JSON contract — not a shared Python package — is the
boundary. This client could also be exercised **outside** Cinema 4D (plain Python)
for testing, since it is pure stdlib.
