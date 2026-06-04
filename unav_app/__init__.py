"""UNAV-SA standalone application (2D/3D navigator UI).

``unav_app`` is the standalone desktop/visual application built on top of
:mod:`unav_core`. It provides catalog **search**, object **inspection**,
**navigator control**, **route/mission** editing, and a 2D map / 3D space view:

* application shell      (:mod:`unav_app.desktop`)
* map/space viewport     (:mod:`unav_app.viewport`)
* UI views and widgets   (:mod:`unav_app.ui`)

The app *uses* the core; it contains no astronomy logic of its own. The UI is
intentionally not implemented at this stage of the project.
"""

__all__: list[str] = []
