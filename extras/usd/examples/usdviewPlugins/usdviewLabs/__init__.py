#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

"""Fork-local usdview UX experiments."""

from pxr import Tf
from pxr.Usdviewq.plugin import PluginContainer


class UsdviewLabsContainer(PluginContainer):
    def registerPlugins(self, plugRegistry, usdviewApi):
        palette = self.deferredImport(".palette")
        hud = self.deferredImport(".hud")
        voiceBridge = self.deferredImport(".voice_bridge")
        pttHotkey = self.deferredImport(".ptt_hotkey")

        self._showPalette = plugRegistry.registerCommandPlugin(
            "UsdviewLabs.showPalette",
            "Command + Query Palette",
            palette.showPalette,
            "Open the experimental command and read-only query palette")

        self._showHud = plugRegistry.registerCommandPlugin(
            "UsdviewLabs.showContextHud",
            "Show Context HUD",
            hud.showContextHud,
            "Show lightweight current usdview context")

        self._hideHud = plugRegistry.registerCommandPlugin(
            "UsdviewLabs.hideContextHud",
            "Hide Context HUD",
            hud.hideContextHud,
            "Hide the experimental context HUD")

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

        self._enablePtt = plugRegistry.registerCommandPlugin(
            "UsdviewLabs.enablePttHotkey",
            "Enable Hold-to-Talk Hotkey",
            pttHotkey.enablePttHotkey,
            "Enable Ctrl+Shift+Space lifecycle signaling to a local stage manager")

        self._disablePtt = plugRegistry.registerCommandPlugin(
            "UsdviewLabs.disablePttHotkey",
            "Disable Hold-to-Talk Hotkey",
            pttHotkey.disablePttHotkey,
            "Disable the hold-to-talk lifecycle hotkey")

    def configureView(self, plugRegistry, plugUIBuilder):
        menu = plugUIBuilder.findOrCreateMenu("Labs")
        menu.addItem(self._showPalette, shortcut="Ctrl+K")
        menu.addItem(self._showHud, shortcut="Ctrl+Shift+H")
        menu.addItem(self._hideHud)
        menu.addSeparator()
        menu.addItem(self._startVoiceBridge)
        menu.addItem(self._stopVoiceBridge)
        menu.addSeparator()
        menu.addItem(self._enablePtt)
        menu.addItem(self._disablePtt)


Tf.Type.Define(UsdviewLabsContainer)
