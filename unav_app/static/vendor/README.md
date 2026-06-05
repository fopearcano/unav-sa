# Vendored third-party libraries

These are committed, unmodified third-party files so the standalone UI needs **no
build step and no runtime CDN** (per `docs/STANDALONE_APP_STACK.md`).

## three.module.min.js

- **Library:** [Three.js](https://threejs.org/)
- **Version:** r160
- **Format:** single-file ES module (imported via the import map in `index.html`)
- **License:** MIT (license header retained in the file)
- **Source:** https://unpkg.com/three@0.160.0/build/three.module.min.js

Used by `unav_app/static/viewport3d.js` for the 3D point-space viewport. To
update, replace this file with a newer pinned build and update this note.
