"""The ModulePanel abstract interface.

Each suite module that wants to appear as a tab in the unified GUI
subclasses ``ModulePanel`` and returns a QWidget from ``build()``.
The host window takes care of the rest (tab frame, export menu,
branding editor).

Registration is programmatic via ``register_panel(name, factory)`` or
via the entry-point group ``metcore.gui_panels``.

Deliberately Qt-agnostic in the public surface so the panel contract
can be tested without importing Qt in headless CI.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

import importlib
import importlib.metadata as ilm
from abc import ABC, abstractmethod
from typing import Any, Callable


# ──────────────────────────────────────────────────────────────────────────────
#  The contract
# ──────────────────────────────────────────────────────────────────────────────

class ModulePanel(ABC):
    """One tab in the unified GUI.

    Subclass and implement ``display_name`` / ``build()`` / ``on_run()``.
    """

    # Title shown on the tab; keep short.
    display_name: str = "module"

    # Short description shown in hover tooltip.
    description: str = ""

    # Module slug (matches the PyPI package slug, e.g. "kernel-audit").
    slug: str = ""

    # Specialty group this panel belongs to (outer tab). Examples:
    #   "Quantum", "Classical & Rheology", "Neural", "Diagnostics".
    domain: str = "General"

    def __init__(self) -> None:
        self._widget: Any = None     # built lazily

    @abstractmethod
    def build(self) -> Any:
        """Build and return the root QWidget of this panel.

        Implementers may import PyQt6 inside this method so the class
        itself stays importable without Qt (important for headless
        tests and for lazy-loading in the host window).
        """

    def on_run(self) -> None:
        """Called when the user presses the panel's main action button.

        Default: no-op. Override for modules that have a runnable
        action (most tools do).
        """

    def on_export(self) -> None:
        """Called when the user presses *Export* on this panel.

        Default: no-op. Modules with a figure should open the export
        dialog and persist to disk via ``metcore_export.export_all``.
        """


# ──────────────────────────────────────────────────────────────────────────────
#  Registry
# ──────────────────────────────────────────────────────────────────────────────

_REGISTRY: dict[str, Callable[[], ModulePanel]] = {}


def register_panel(name: str, factory: Callable[[], ModulePanel]) -> None:
    """Register a panel factory under ``name`` (usually the module slug)."""
    if not callable(factory):
        raise TypeError("factory must be callable returning a ModulePanel")
    _REGISTRY[name] = factory


def registered_panels() -> dict[str, Callable[[], ModulePanel]]:
    """Return a copy of the current panel registry.

    On first call, also loads panels declared via the
    ``metcore.gui_panels`` entry-point group in any installed
    distribution. Failures to load are silent - a missing optional
    module must not break the host.
    """
    if not getattr(registered_panels, "_discovered", False):
        _discover_entry_points()
        registered_panels._discovered = True  # type: ignore[attr-defined]
    return dict(_REGISTRY)


def _discover_entry_points() -> None:
    eps = ilm.entry_points()
    group = (eps.select(group="metcore.gui_panels")
             if hasattr(eps, "select")
             else eps.get("metcore.gui_panels", []))  # type: ignore[attr-defined]
    for ep in group:
        try:
            target = ep.load()
        except Exception:
            continue
        if isinstance(target, type) and issubclass(target, ModulePanel):
            _REGISTRY.setdefault(ep.name, target)
        elif callable(target):
            _REGISTRY.setdefault(ep.name, target)


def panels_by_domain() -> dict[str, dict[str, Callable[[], "ModulePanel"]]]:
    """Group registered panel factories by their ``domain`` (outer GUI tab).

    Returns {domain: {name: factory}}. Headless-testable: it instantiates each
    factory once to read its ``domain``; instantiation must stay Qt-free
    (build() is where Qt lives), which every ModulePanel honours.
    """
    out: dict[str, dict[str, Callable[[], ModulePanel]]] = {}
    for name, factory in registered_panels().items():
        try:
            domain = getattr(factory, "domain", None)
            if domain is None:
                domain = factory().domain
        except Exception:
            domain = "General"
        out.setdefault(domain, {})[name] = factory
    return out
