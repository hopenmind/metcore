"""
Reusable Qt behaviours shared by every panel: a right-click export menu on the
figure, and a debounced "live update" that recomputes when inputs change.

PyQt6 is imported lazily inside the functions, so this module stays importable
without Qt (the panels import it at module load, including in headless tests).

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

import weakref
from typing import Any

#: every wired panel registers here so theme/branding changes can repaint all
_LIVE_PANELS: list = []


def _basename(panel) -> str:
    fn = getattr(panel, "export_basename", None)
    if callable(fn):
        try:
            return fn()
        except Exception:
            pass
    return (getattr(panel, "slug", None) or "metcore").replace("-", "_")


def _do_export(panel, formats, with_xml: bool) -> None:  # pragma: no cover - Qt/display
    from PyQt6.QtWidgets import QFileDialog
    from metcore_export import export_xml
    if getattr(panel, "_fig", None) is None:
        return
    outdir = QFileDialog.getExistingDirectory(panel._widget, "Export to folder")
    if not outdir:
        return
    base = _basename(panel)
    msg = ""
    try:
        res = panel.ctrl.export(panel._fig, outdir, basename=base, formats=formats)
        msg = f"Exported {len(res)} file(s)"
    except Exception as exc:
        msg = f"Export error: {exc}"
    if with_xml and getattr(panel, "_result", None) is not None:
        try:
            export_xml(panel._result, outdir, base)
            msg += " + XML"
        except Exception as exc:
            msg += f" (XML failed: {exc})"
    if hasattr(panel, "_status"):
        panel._status.setText(f"{msg} -> {outdir}")


def _do_attach(panel, keys) -> None:  # pragma: no cover - Qt/display
    """Write tabular / composite attachments (CSV, Excel, image+table) for the
    current result into a chosen folder."""
    from PyQt6.QtWidgets import QFileDialog
    from metcore_export import write_attachment
    if getattr(panel, "_result", None) is None:
        return
    outdir = QFileDialog.getExistingDirectory(panel._widget, "Export to folder")
    if not outdir:
        return
    base = _basename(panel)
    ctrl = panel.ctrl
    try:
        series = ctrl.series(panel._result) if hasattr(ctrl, "series") else None
    except Exception:
        series = None

    def make_fig():
        return ctrl.make_figure(panel._result)

    written, errs = [], []
    for k in keys:
        try:
            write_attachment(k, outdir=outdir, basename=base,
                             result=panel._result, series=series,
                             make_figure=make_fig)
            written.append(k)
        except Exception as exc:  # noqa: BLE001
            errs.append(f"{k}: {exc}")
    msg = ("Wrote " + ", ".join(written)) if written else "Nothing written"
    if errs:
        msg += " | errors: " + "; ".join(errs)
    if hasattr(panel, "_status"):
        panel._status.setText(f"{msg} -> {outdir}")


def attach_figure_export_menu(panel) -> None:  # pragma: no cover - Qt/display
    """Right-click the figure to export one format, all formats, or figure+XML."""
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QMenu
    from metcore_export import ACADEMIC_FORMATS

    canvas = panel._canvas
    canvas.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

    def show_menu(pos):
        menu = QMenu(canvas)
        for key, ext, _dpi in ACADEMIC_FORMATS:
            act = menu.addAction(f"Export {key} (.{ext})")
            act.triggered.connect(lambda _=False, k=key: _do_export(panel, [k], False))
        menu.addSeparator()
        menu.addAction("Export all 7 formats...").triggered.connect(
            lambda: _do_export(panel, None, False))
        menu.addAction("Export figure + data (XML)...").triggered.connect(
            lambda: _do_export(panel, ["png600"], True))
        menu.addSeparator()
        from metcore_export import ATTACHMENTS
        data_menu = menu.addMenu("Attach data...")
        for att in ATTACHMENTS:
            if att.key == "xml":
                continue  # already offered as "figure + data (XML)" above
            data_menu.addAction(att.label).triggered.connect(
                lambda _=False, k=att.key: _do_attach(panel, [k]))
        data_menu.addSeparator()
        data_menu.addAction("All data attachments").triggered.connect(
            lambda: _do_attach(panel, [a.key for a in ATTACHMENTS]))
        menu.addSeparator()
        menu.addAction("Branding...").triggered.connect(lambda: _edit_branding(panel))
        menu.exec(canvas.mapToGlobal(pos))

    canvas.customContextMenuRequested.connect(show_menu)


def _edit_branding(panel) -> None:  # pragma: no cover - Qt/display
    from metcore_gui.branding_dialog import BrandingDialog
    BrandingDialog(panel._widget).exec()
    # repaint every open panel with the (possibly) new theme immediately
    refresh_all_panels()


def make_live_checkbox(panel, layout=None, default_on=None):  # pragma: no cover - Qt
    """Add a 'Live update' checkbox; while checked, input changes recompute
    (debounced ~350 ms) by calling panel.on_run. default_on=None reads the
    user preference (Edit > Preferences)."""
    from PyQt6.QtWidgets import QCheckBox
    from PyQt6.QtCore import QTimer

    if default_on is None:
        from metcore_gui.preferences import Settings
        default_on = Settings.load().live_update_default
    cb = QCheckBox("Live update")
    cb.setChecked(bool(default_on))
    timer = QTimer()
    timer.setSingleShot(True)
    timer.setInterval(350)
    timer.timeout.connect(panel.on_run)

    def schedule(*_a):
        if cb.isChecked():
            timer.start()

    cb.toggled.connect(lambda on: on and panel.on_run())

    for w in getattr(panel, "_inputs", {}).values():
        for sig_name in ("valueChanged", "currentTextChanged", "textChanged"):
            sig = getattr(w, sig_name, None)
            if sig is not None:
                try:
                    sig.connect(schedule)
                    break
                except Exception:
                    pass
    panel._live_cb = cb
    panel._live_timer = timer
    if layout is not None:
        layout.addWidget(cb)
    return cb




def refresh_canvas(panel) -> None:  # pragma: no cover - Qt/display
    """Redraw the live figure: curve, plus the embedded value table when the
    'Embedded data table' toggle is on. Every redraw path funnels through here
    so the on-screen figure and the WYSIWYG export always match. Any problem
    is written to the panel status line - never swallowed invisibly."""
    if getattr(panel, "_result", None) is None or getattr(panel, "_fig", None) is None:
        return
    try:
        panel.ctrl.draw_into(panel._fig, panel._result)
    except Exception as exc:
        if hasattr(panel, "_status"):
            panel._status.setText(f"Refresh error: {exc}")
        return
    if getattr(panel, "_table_on", False) and hasattr(panel.ctrl, "series"):
        try:
            from metcore_export import add_data_table
            add_data_table(panel._fig, panel.ctrl.series(panel._result),
                           max_rows=int(getattr(panel, "_table_rows", 12)))
        except Exception as exc:
            if hasattr(panel, "_status"):
                panel._status.setText(f"Table error: {exc}")
    if getattr(panel, "_canvas", None) is not None:
        panel._canvas.draw_idle()


def refresh_all_panels() -> None:  # pragma: no cover - Qt/display
    """Repaint every wired panel (used after the color theme / branding
    changes, so the new colors show up immediately on screen)."""
    for ref in list(_LIVE_PANELS):
        panel = ref()
        if panel is None:
            _LIVE_PANELS.remove(ref)
            continue
        try:
            refresh_canvas(panel)
        except Exception:
            pass


def make_table_toggle(panel, layout=None):  # pragma: no cover - Qt
    """Checkbox under the figure: paint the sampled value table INTO the live
    figure (the canvas splits: curve on top, table below). A spinbox sets how
    many evenly-sampled rows are shown. Exports then ship what is displayed."""
    from PyQt6.QtWidgets import QCheckBox, QSpinBox, QLabel
    from metcore_gui.preferences import Settings
    n_default = Settings.load().table_rows_default
    cb = QCheckBox("Embedded data table")
    rows = QSpinBox(); rows.setRange(6, 30); rows.setValue(n_default)
    rows.setToolTip("Rows sampled evenly along the curve")
    panel._table_on = False
    panel._table_rows = n_default

    def changed(*_a):
        panel._table_on = cb.isChecked()
        panel._table_rows = int(rows.value())
        refresh_canvas(panel)

    cb.toggled.connect(changed)
    rows.valueChanged.connect(changed)
    if layout is not None:
        layout.addWidget(cb)
        layout.addWidget(QLabel("rows:"))
        layout.addWidget(rows)
    panel._table_cb = cb
    return cb


def wire_panel_features(panel, button_layout=None) -> None:  # pragma: no cover - Qt
    """One call from a panel's build(): right-click export menu, live checkbox,
    and the embedded-data-table toggle."""
    attach_figure_export_menu(panel)
    make_live_checkbox(panel, button_layout)
    make_table_toggle(panel, button_layout)
    _LIVE_PANELS.append(weakref.ref(panel))
