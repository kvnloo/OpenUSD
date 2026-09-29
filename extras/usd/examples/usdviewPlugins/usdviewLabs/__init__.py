#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

"""Fork-local usdview UX experiments.

The package is intentionally isolated from usdview core so experiments can be
measured before any individual UX primitive is proposed upstream.
"""

from pxr import Tf
from pxr.Usdviewq.plugin import PluginContainer


class UsdviewLabsContainer(PluginContainer):
    def registerPlugins(self, plugRegistry, usdviewApi):
        palette = self.deferredImport(".palette")
        voiceBridge = self.deferredImport(".voice_bridge")

        self._showPalette = plugRegistry.registerCommandPlugin(
            "UsdviewLabs.showPalette",
            "Command Palette",
            palette.showPalette,
            "Open the experimental usdview command palette")

        self._startVoiceBridge = plugRegistry.registerCommandPlugin(
            "UsdviewLabs.startVoiceBridge",
            "Start Voice Bridge",
            voiceBridge.startVoiceBridge,
            "Start the local-only transcript bridge")

        self._stopVoiceBridge = plugRegistry.registerCommandPlugin(
            "UsdviewLabs.stopVoiceBridge",
            "Stop Voice Bridge",
            voiceBridge.stopVoiceBridge,
            "Stop the local-only transcript bridge")

    def configureView(self, plugRegistry, plugUIBuilder):
        menu = plugUIBuilder.findOrCreateMenu("Labs")
        menu.addItem(self._showPalette, shortcut="Ctrl+K")
        menu.addSeparator()
        menu.addItem(self._startVoiceBridge)
        menu.addItem(self._stopVoiceBridge)


Tf.Type.Define(UsdviewLabsContainer)
