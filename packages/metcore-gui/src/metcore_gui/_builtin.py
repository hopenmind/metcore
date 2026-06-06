"""
Explicit registration of the built-in GUI panels.

Entry-point discovery (importlib.metadata, group "metcore.gui_panels") is the
normal path, but it is unreliable inside a frozen PyInstaller bundle because the
distribution metadata is often not shipped. The host window falls back to this
module when the registry comes up empty, so the packaged executable always shows
its tabs.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

from metcore_gui.panel import register_panel

# slug -> factory module path. Imported lazily so this file stays light.
_BUILTINS = {
    "obliquity-ng":     "metcore_gui.ng_panel:make_panel",
    "memkern-rheology": "metcore_gui.rheology_panel:make_panel",
    "boltz-kernel":     "metcore_gui.quantum_panel:make_panel",
    "paper3a-neural":   "metcore_gui.neural_panel:make_panel",
    "met-shortcuts":    "metcore_gui.shortcuts_panel:make_panel",
}


def register_builtin_panels() -> int:
    """Register every built-in panel directly. Returns how many were added."""
    import importlib
    added = 0
    for slug, target in _BUILTINS.items():
        mod_name, _, attr = target.partition(":")
        try:
            factory = getattr(importlib.import_module(mod_name), attr)
        except Exception:
            continue
        register_panel(slug, factory)
        added += 1
    return added
