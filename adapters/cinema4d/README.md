# adapters/cinema4d/

Cinema 4D adapter for UNAV-SA. **Future work — not implemented yet.**

This will be the **first** DCC adapter, built *after* the standalone core and
app are useful on their own. It is a **client**: it consumes UNAV-SA interchange
/ local API and maps results into Cinema 4D scene objects. It does not own
astronomy logic and must not require heavy scientific dependencies inside the
Cinema 4D Python runtime.

> Reminder: UNAV-SA is **not** a Cinema 4D plugin. Cinema 4D is an adapter on
> top of the standalone engine.

See [`docs/DCC_ADAPTER_STRATEGY.md`](../../docs/DCC_ADAPTER_STRATEGY.md).
