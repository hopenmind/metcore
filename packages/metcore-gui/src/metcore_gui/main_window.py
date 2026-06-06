"""MainWindow - host for all suite panels.

Lifts the branding + 7-format export dialogs from the legacy
BoltZ-Kernel GUI and generalises them so every panel benefits.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

from typing import Any

from metcore_gui.panel import ModulePanel, registered_panels, panels_by_domain


def build_main_window(show: bool = True):
    """Instantiate and return the QMainWindow.

    ``show=False`` skips ``.show()`` so the function can be unit-tested
    headlessly (under QT_QPA_PLATFORM=offscreen).
    """
    from PyQt6.QtWidgets import (
        QMainWindow,
        QTabWidget,
        QStatusBar,
        QMenuBar,
        QMessageBox,
        QLabel,
        QWidget,
        QVBoxLayout,
    )
    from PyQt6.QtGui import QAction

    groups = panels_by_domain()
    if not groups:
        # frozen bundle: entry-points unavailable, register built-ins directly
        from metcore_gui._builtin import register_builtin_panels
        register_builtin_panels()
        groups = panels_by_domain()

    window = QMainWindow()
    window.setWindowTitle("Metcore")
    window.resize(1200, 800)
    _apply_window_icon(window)

    # Outer tabs = scientific specialties; inner tabs = tools within a domain.
    tabs = QTabWidget()
    window.setCentralWidget(tabs)

    # Stable, meaningful ordering of specialty tabs.
    _ORDER = ["Quantum", "Classical & Rheology", "Neural", "Diagnostics", "Shortcuts", "General"]
    domains = sorted(groups, key=lambda d: (_ORDER.index(d) if d in _ORDER else 99, d))

    for domain in domains:
        inner = QTabWidget()
        inner.setTabPosition(QTabWidget.TabPosition.West)
        for name, factory in groups[domain].items():
            try:
                panel: ModulePanel = factory()
                widget = panel.build()
                label = getattr(panel, "display_name", name)
            except Exception as exc:  # noqa: BLE001
                widget = _placeholder(f"{name} failed to load:\n{exc!r}")
                label = name
            inner.addTab(widget, label)
        tabs.addTab(inner, domain)

    if not groups:
        tabs.addTab(_placeholder(
            "No suite modules installed with a GUI panel yet.\n\n"
            "Try:  pip install kernel-audit memkern-ladder hpc-oracle"
        ), "Getting started")

    # Status bar shows suite version
    bar = QStatusBar()
    try:
        from importlib.metadata import version
        v = version("hopenmind-suite")
    except Exception:
        v = "(dev)"
    bar.showMessage(f"Hope 'n Mind Suite v{v}")
    window.setStatusBar(bar)

    # Menu - File / Branding / Export
    _build_menus(window, tabs)

    if show:
        window.show()
    return window


def _icon_path() -> str | None:
    """Locate the bundled app icon in dev, wheel, or frozen layouts."""
    import os
    # 1) packaged asset inside metcore_gui (works for pip install + dev)
    try:
        from importlib.resources import files
        p = files("metcore_gui") / "assets" / "metcore.png"
        if p.is_file():
            return str(p)
    except Exception:
        pass
    # 2) PyInstaller bundle: alongside the executable / in _MEIPASS
    import sys
    for base in (getattr(sys, "_MEIPASS", None), os.path.dirname(sys.argv[0])):
        if base:
            for name in ("metcore.png", "metcore.ico"):
                cand = os.path.join(base, name)
                if os.path.isfile(cand):
                    return cand
    return None


def _apply_window_icon(window) -> None:
    """Set the window/taskbar icon; never fails the app if the icon is absent."""
    try:
        path = _icon_path()
        if not path:
            return
        from PyQt6.QtGui import QIcon
        from PyQt6.QtWidgets import QApplication
        icon = QIcon(path)
        window.setWindowIcon(icon)
        app = QApplication.instance()
        if app is not None:
            app.setWindowIcon(icon)
    except Exception:
        pass


def _placeholder(text: str):
    from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget
    from PyQt6.QtCore import Qt
    w = QWidget()
    lay = QVBoxLayout(w)
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setWordWrap(True)
    lay.addWidget(lbl)
    return w


def _build_menus(window, tabs) -> None:
    """Classic menu bar: File / Edit / Tools / ?"""
    from PyQt6.QtGui import QAction
    from PyQt6.QtWidgets import QMessageBox

    menubar = window.menuBar()
    file_menu = menubar.addMenu("&File")
    edit_menu = menubar.addMenu("&Edit")
    tools_menu = menubar.addMenu("&Tools")
    help_menu = menubar.addMenu("&?")

    # ── File ──
    act_export = QAction("&Export active panel…", window)

    def _do_export():
        idx = tabs.currentIndex()
        if idx < 0:
            return
        title = tabs.tabText(idx)
        panels = registered_panels()
        panel = panels.get(title) or panels.get(title.lower())
        if panel:
            try:
                inst = panel() if callable(panel) else None
                if inst and hasattr(inst, "on_export"):
                    inst.on_export()
                    return
            except Exception:
                pass
        QMessageBox.information(window, "Export",
                                "This panel does not yet implement export.")
    act_export.triggered.connect(_do_export)
    file_menu.addAction(act_export)
    file_menu.addSeparator()
    act_quit = QAction("&Quit", window)
    act_quit.triggered.connect(window.close)
    file_menu.addAction(act_quit)

    # ── Edit ──
    act_brand = QAction("&Branding && colors…", window)

    def _open_brand_dialog():
        from metcore_gui.branding_dialog import BrandingDialog
        BrandingDialog(window).exec()
        # repaint every open panel so the new theme shows immediately
        from metcore_gui.panel_features import refresh_all_panels
        refresh_all_panels()
    act_brand.triggered.connect(_open_brand_dialog)
    edit_menu.addAction(act_brand)

    act_prefs = QAction("&Preferences…", window)

    def _open_prefs():
        from metcore_gui.preferences import open_preferences_dialog
        open_preferences_dialog(window)
    act_prefs.triggered.connect(_open_prefs)
    edit_menu.addAction(act_prefs)

    # ── Tools ──
    act_batch = QAction("&Batch processing…", window)

    def _open_batch():
        from metcore_gui.batch_panel import open_batch_dialog
        open_batch_dialog(window)
    act_batch.triggered.connect(_open_batch)
    tools_menu.addAction(act_batch)

    # ── ? (Tutorial) ──
    act_tut = QAction("&Tutorial && purpose…", window)

    def _tutorial():
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextBrowser
        dlg = QDialog(window)
        dlg.setWindowTitle("Metcore - what it is for")
        dlg.resize(720, 560)
        lay = QVBoxLayout(dlg)
        txt = QTextBrowser()
        txt.setOpenExternalLinks(True)
        txt.setHtml("""
<h2>What Metcore is for</h2>
<p><b>Metcore answers one expensive question: does the memory of your system
actually matter - and is heavy non-Markovian computation worth it?</b></p>
<p>Before committing weeks of simulation time (HEOM, pseudomodes, TEDOPA,
quantum hardware) or silently accepting the standard Markovian shortcut
(Lindblad), you can <i>measure</i> the answer instead of guessing it. Every
verdict Metcore produces is a number you can cite in a paper or show a
referee - not a community convention.</p>

<h3>The decision pipeline</h3>
<ol>
<li><b>Bring your memory kernel C(&tau;)</b> - a quantum bath correlation,
a rheological relaxation modulus G(t), a synaptic kernel K(t). Each tab can
also build canonical ones for you.</li>
<li><b>Embeddability</b> - is the kernel <i>rational</i> (finite memory: the
Markov Embedding Theorem applies exactly) or <i>power-law / sub-ohmic</i>
(only approximate treatments exist)? This is the scope gate: run it first.</li>
<li><b>K, the embedding order</b> - how many auxiliary modes an exact
treatment costs. K sizes your compute bill: a small K means the memory can
be compiled away cheaply; a large K tells you the heavy methods are justified.</li>
<li><b>CPTP certificate</b> - is a Markovian (Lindblad) description even
admissible for this kernel, and on which time windows does it break?</li>
<li><b>Lindblad gap</b> - if you use the Markovian model anyway, how wrong is
it, quantified over time (peak and integrated error).</li>
<li><b>N<sub>G</sub></b> - how much memory there is, as a single geometric
number: 0 for Markovian dynamics, &gt; 0 when coherence flows back.</li>
</ol>
<p><b>full_diagnosis</b> chains all of the above and ends with a plain-language
summary. If you only run one thing, run that.</p>

<h3>The tabs</h3>
<p><b>Quantum</b>: spectral density J(&omega;) &rarr; bath correlation &rarr;
diagnosis. <b>Classical &amp; Rheology</b>: Maxwell-Wiechert / Prony spectrum
of a measured G(t). <b>Neural</b>: retarded synaptic kernels.
<b>Diagnostics</b>: N<sub>G</sub> on canonical qubit channels.</p>

<h3>Getting your results out</h3>
<p>Right-click any figure: 7 academic image formats, CSV / Excel of the
plotted numbers, XML sidecar, or an image with the value table embedded.
The same table can be shown live with the "Embedded data table" checkbox.
<b>Tools &gt; Batch processing</b> runs a CSV of parameter sets in one go.
<b>Edit &gt; Branding &amp; colors</b> puts your lab's logo, name and brand
colors on everything you export. The same tools are exposed to any LLM via
the bundled MCP server ("metcore").</p>

<p><i>DOI: <a href="https://doi.org/10.5281/zenodo.20557167">
10.5281/zenodo.20557167</a> - by Hope \'n Mind</i></p>
""")
        lay.addWidget(txt)
        dlg.exec()
    act_tut.triggered.connect(_tutorial)
    help_menu.addAction(act_tut)

    # ── ? (About) ──
    act_about = QAction("&About Metcore…", window)

    def _about():
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel
        from PyQt6.QtGui import QPixmap
        from PyQt6.QtCore import Qt
        dlg = QDialog(window)
        dlg.setWindowTitle("About Metcore")
        lay = QVBoxLayout(dlg)
        path = _icon_path()
        if path:
            logo = QLabel()
            logo.setPixmap(QPixmap(path).scaled(
                96, 96, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
            logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(logo)
        try:
            from importlib.metadata import version
            ver = version("metcore-gui")
        except Exception:
            ver = "dev"
        txt = QLabel(
            "<h2 align=\'center\'>Metcore</h2>"
            "<p align=\'center\'>The core of the Markov Embedding Theorem.<br>"
            "Non-Markovian dynamics toolkit.</p>"
            f"<p align=\'center\'>Version {ver}</p>"
            "<p align=\'center\'>DOI: <a href=\'https://doi.org/10.5281/zenodo.20557167\'>"
            "10.5281/zenodo.20557167</a><br>"
            "<a href=\'https://github.com/hopenmind/metcore\'>github.com/hopenmind/metcore</a><br>"
            "contact@hopenmind.com</p>"
            "<p align=\'center\'><i>by Hope \'n Mind</i></p>")
        txt.setOpenExternalLinks(True)
        lay.addWidget(txt)
        dlg.exec()
    act_about.triggered.connect(_about)
    help_menu.addAction(act_about)
