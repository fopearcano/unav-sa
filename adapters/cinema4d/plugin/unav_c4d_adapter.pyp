"""UNAV-SA — Cinema 4D adapter plugin entry point.

A thin **CommandData** plugin that opens the adapter dialog. It connects to a
running UNAV-SA local server and imports camera/mission data — it does **no**
astronomy, fetches **no** catalogs, and uses **only** the ``c4d`` SDK + the Python
standard library (see ``adapters/cinema4d/docs/C4D_DATA_OWNERSHIP_RULES.md``).

Install: copy the ``plugin/`` folder into Cinema 4D's ``plugins`` directory and
restart C4D (see ``adapters/cinema4d/docs/INSTALL_C4D_ADAPTER.md``). Open it from
the *Extensions* menu while the UNAV-SA server is running.
"""

import os
import sys

# Make the sibling modules (client/ui/camera_import/timeline_bake) importable when
# Cinema 4D executes this .pyp from the plugins folder.
_PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
if _PLUGIN_DIR not in sys.path:
    sys.path.insert(0, _PLUGIN_DIR)

import c4d
from c4d import plugins

import ui

# Placeholder plugin id. Register a unique id at https://plugincafe.maxon.net/
# before any public release; 1000001 is a development-only value that may clash.
PLUGIN_ID = 1000001
PLUGIN_NAME = "UNAV-SA Adapter"


class UnavAdapterCommand(plugins.CommandData):
    """Opens the adapter dialog from the Extensions menu."""

    _dialog = None

    def _get_dialog(self):
        if self._dialog is None:
            self._dialog = ui.UnavAdapterDialog()
        return self._dialog

    def Execute(self, doc):  # noqa: N802 - C4D SDK signature
        return self._get_dialog().Open(
            c4d.DLG_TYPE_ASYNC, pluginid=PLUGIN_ID, defaultw=440, defaulth=260
        )

    def RestoreLayout(self, sec_ref):  # noqa: N802 - C4D SDK signature
        return self._get_dialog().Restore(pluginid=PLUGIN_ID, secret=sec_ref)


def main():
    plugins.RegisterCommandPlugin(
        id=PLUGIN_ID,
        str=PLUGIN_NAME,
        info=0,
        icon=None,
        help="Connect to the UNAV-SA local server and import camera/mission data.",
        dat=UnavAdapterCommand(),
    )


if __name__ == "__main__":
    main()
