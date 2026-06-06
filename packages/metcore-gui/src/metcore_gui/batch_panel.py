"""
Batch processing dialog - a thin Qt front-end over metcore_gui.batch.run_batch.

Lazy Qt imports: importable without a display (the host imports it only when the
user opens the dialog).

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

# (label, module, controller class) for each tool that supports batch
_CONTROLLERS = [
    ("Diagnostics: N_G / obliquity", "metcore_gui.ng_panel", "NGController"),
    ("Classical: Rheology G(t)", "metcore_gui.rheology_panel", "RheologyController"),
    ("Quantum: bath J(omega)", "metcore_gui.quantum_panel", "QuantumController"),
    ("Neural: synaptic kernel", "metcore_gui.neural_panel", "NeuralController"),
    ("Shortcuts: analytic one-stroke", "metcore_gui.shortcuts_panel", "ShortcutsController"),
]


def open_batch_dialog(parent=None) -> None:  # pragma: no cover - Qt/display
    import importlib
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QPushButton,
        QLabel, QLineEdit, QCheckBox, QFileDialog, QGridLayout, QWidget,
    )
    from metcore_export import ACADEMIC_FORMATS, ATTACHMENTS
    from metcore_gui.batch import run_batch, load_jobs_csv
    from metcore_gui.preferences import Settings
    prefs = Settings.load()

    dlg = QDialog(parent)
    dlg.setWindowTitle("Batch processing")
    dlg.resize(580, 520)
    root = QVBoxLayout(dlg)

    form = QFormLayout()
    tool = QComboBox()
    for label, _m, _c in _CONTROLLERS:
        tool.addItem(label)
    form.addRow("Tool:", tool)

    state: dict = {"jobs": []}
    load_btn = QPushButton("Load CSV of jobs...")
    jobs_lbl = QLabel("No jobs loaded. CSV header = parameter names, one job per row.")

    def load_csv():
        path, _ = QFileDialog.getOpenFileName(dlg, "Choose a CSV of jobs",
                                              filter="CSV files (*.csv)")
        if not path:
            return
        try:
            state["jobs"] = load_jobs_csv(path)
            jobs_lbl.setText(f"{len(state['jobs'])} job(s) loaded.")
        except Exception as exc:
            jobs_lbl.setText(f"CSV error: {exc}")

    load_btn.clicked.connect(load_csv)
    form.addRow(load_btn, jobs_lbl)

    out = QLineEdit(prefs.output_dir_default)
    out_btn = QPushButton("Folder...")
    out_btn.clicked.connect(
        lambda: out.setText(QFileDialog.getExistingDirectory(dlg, "Output folder") or out.text()))
    out_row = QHBoxLayout(); out_row.addWidget(out); out_row.addWidget(out_btn)
    ow = QWidget(); ow.setLayout(out_row)
    form.addRow("Output folder:", ow)

    pattern = QLineEdit("{name}")
    pattern.setToolTip("e.g. {name}  or  {index}_{channel}  (any job parameter)")
    form.addRow("Filename pattern:", pattern)

    xml_cb = QCheckBox("Also write an XML data sidecar per job")
    xml_cb.setChecked(True)
    form.addRow("", xml_cb)
    root.addLayout(form)

    root.addWidget(QLabel("Image formats:"))
    grid = QGridLayout()
    fmt_boxes: dict = {}
    for i, (key, ext, _dpi) in enumerate(ACADEMIC_FORMATS):
        cb = QCheckBox(f"{key} (.{ext})")
        if key in prefs.export_formats_default:
            cb.setChecked(True)
        fmt_boxes[key] = cb
        grid.addWidget(cb, i // 3, i % 3)
    gw = QWidget(); gw.setLayout(grid)
    root.addWidget(gw)

    root.addWidget(QLabel("Data attachments (per job):"))
    arow = QHBoxLayout()
    att_boxes: dict = {}
    for att in ATTACHMENTS:
        if att.key == "xml":
            continue  # the XML sidecar already has its own checkbox above
        cb = QCheckBox(att.label)
        if att.key == "csv":
            cb.setChecked(True)
        att_boxes[att.key] = cb
        arow.addWidget(cb)
    aw = QWidget(); aw.setLayout(arow)
    root.addWidget(aw)

    status = QLabel("")
    run_btn = QPushButton("Run batch")

    def run():
        _label, mod, cls = _CONTROLLERS[tool.currentIndex()]
        if not state["jobs"]:
            status.setText("Load a CSV of jobs first."); return
        if not out.text().strip():
            status.setText("Choose an output folder."); return
        formats = [k for k, cb in fmt_boxes.items() if cb.isChecked()] or ["png600"]
        status.setText("Running...")
        try:
            controller = getattr(importlib.import_module(mod), cls)()
            attachments = [k for k, cb in att_boxes.items() if cb.isChecked()]
            rep = run_batch(controller, state["jobs"], out.text().strip(),
                            formats=formats, write_xml=xml_cb.isChecked(),
                            attachments=attachments,
                            name_pattern=pattern.text() or "{name}")
            status.setText(
                f"Done: {rep.n_ok}/{rep.n_jobs} ok, {rep.n_failed} failed  ->  {out.text()}")
        except Exception as exc:
            status.setText(f"Batch error: {exc}")

    run_btn.clicked.connect(run)
    root.addWidget(run_btn)
    root.addWidget(status)
    dlg.exec()
