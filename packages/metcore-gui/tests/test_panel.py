"""Tests for hopenmind-gui — panel contract is Qt-free so these
are headless-safe.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

import pytest

from metcore_gui import ModulePanel, register_panel, registered_panels
from metcore_gui.panel import _REGISTRY


class _DemoPanel(ModulePanel):
    display_name = "Demo"
    slug = "demo"

    def build(self):
        return object()  # placeholder QWidget in real use


@pytest.fixture(autouse=True)
def _reset_registry():
    snapshot = dict(_REGISTRY)
    yield
    _REGISTRY.clear()
    _REGISTRY.update(snapshot)


def test_cannot_instantiate_abstract_base():
    with pytest.raises(TypeError):
        ModulePanel()  # type: ignore[abstract]


def test_register_and_list_panels():
    register_panel("demo", _DemoPanel)
    panels = registered_panels()
    assert "demo" in panels
    assert panels["demo"] is _DemoPanel


def test_register_panel_rejects_noncallable():
    with pytest.raises(TypeError):
        register_panel("x", 42)  # type: ignore[arg-type]


def test_default_on_run_and_on_export_are_noops():
    p = _DemoPanel()
    # No-op methods must not raise
    p.on_run()
    p.on_export()


def test_registry_entry_point_discovery_is_lazy():
    # After a fresh import, registered_panels() triggers discovery once
    # and sets a sentinel flag
    registered_panels()
    assert getattr(registered_panels, "_discovered", False)
