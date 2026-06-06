"""hopenmind-gui — unified PyQt6 desktop app for the suite.

Public surface:
  * ``ModulePanel``   — the abstract interface every module-specific
    tab implements.
  * ``MainWindow``    — host window, aggregates panels.
  * ``register_panel(name, factory)`` — programmatic registration.

Modules are also auto-discovered via the
``metcore.gui_panels`` entry-point group:

    [project.entry-points."metcore.gui_panels"]
    kernel-audit = "kernel_audit.gui:KernelAuditPanel"

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

from metcore_gui.panel import ModulePanel, register_panel, registered_panels

__all__ = ["ModulePanel", "register_panel", "registered_panels"]

__version__ = "0.1.0"
__author__ = "DESVAUX G.J.Y."
__license__ = "Apache-2.0 OR LicenseRef-HopenMind-Commercial"
from metcore_gui import batch  # noqa: E402,F401
