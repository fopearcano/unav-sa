"""UNAV-SA standalone application (2D/3D navigator UI).

``unav_app`` is the standalone desktop/visual application built on top of
:mod:`unav_core`. It provides catalog **search**, object **inspection**,
**navigator control**, **route/mission** editing, and a 2D map / 3D space view:

* application shell      (:mod:`unav_app.desktop`)
* map/space viewport     (:mod:`unav_app.viewport`)
* UI views and widgets   (:mod:`unav_app.ui`)

The app *uses* the core; it contains no astronomy logic of its own. The first
shell is a minimal static web frontend in ``unav_app/static`` (plain HTML/CSS/JS,
no build step), served by the local API server — see
``docs/STANDALONE_APP_SHELL.md``.
"""

__all__: list[str] = []
