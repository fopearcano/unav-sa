# UNAV-SA — Standalone App Manual Test Checklist

A quick manual acceptance pass for the Phase 10 standalone shell. (Automated
coverage of the server-side pieces lives in `tests/`; the static serving is
checked by `tests/test_app_static.py`.)

## Setup

```bash
pip install -e ".[server]"
python tools/generate_sample_catalog.py --count 100 --seed 42 --output samples/sample_catalog.jsonl
python tools/import_catalog.py --input samples/sample_catalog.jsonl --db data/unav.db --dataset-name sample --enrich
python tools/run_unav_server.py --db data/unav.db --port 8765
```

Open <http://127.0.0.1:8765/> in a browser.

## Checklist

- [ ] **Run local server** — the command above starts without error and prints a
      uvicorn "Application startup complete" line.
- [ ] **Open standalone UI** — the page loads; the top-bar health badge turns
      green and shows `ok · 100 objects`.
- [ ] **Datasets** — the Datasets panel lists `sample` (100 · its source).
- [ ] **Search sample catalog** — type `Sample Star` in Search and submit; the
      results list fills and the status bar shows a count.
- [ ] **Inspect object** — click a result; the Selected object panel shows its
      uid/name/type/source and coordinates.
- [ ] **Navigator state** — edit `far (pc)` and `cone (deg)`, click **Set state**;
      the values persist (re-read from the server). Click **Focus navigator on
      object** with a selected object that has `x/y/z`; the position fields update.
- [ ] **Query visible sector** — click **Query visible sector**; the visible
      count updates and the results list shows the visible objects.
- [ ] **See a simple visual placeholder** — the 2D sky canvas shows scattered
      points (coloured by type); the note shows `N/M plotted`. The 3D panel shows
      the labelled placeholder container.

## Notes / known limitations

- The in-memory default DB is empty; use a `--db` file you have imported into (as
  above), or import via the API first.
- Objects with only Cartesian `x/y/z` (no RA/Dec) are listed but not drawn on the
  2D sky map — the "plotted" count reflects this.
- The 3D view is a placeholder; Three.js rendering of `x/y/z` is a later phase.
- Routes/missions are not yet surfaced in this minimal shell (the API exposes
  them; the UI does not — kept intentionally small).
