"""User preferences: persisted defaults + the Preferences dialog.

The Settings dataclass is Qt-free (headless-testable); the dialog imports
PyQt6 lazily. Stored in ~/.metcore/settings.json next to branding.json.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


def _settings_path() -> Path:
    return Path.home() / ".metcore" / "settings.json"


@dataclass
class Settings:
    live_update_default:    bool = False        # 'Live update' pre-checked
    table_rows_default:     int = 12            # embedded table rows
    export_formats_default: list = field(default_factory=lambda: ["png600"])
    output_dir_default:     str = ""            # pre-filled output folder

    @classmethod
    def load(cls) -> "Settings":
        s = cls()
        try:
            data = json.loads(_settings_path().read_text(encoding="utf-8"))
            for k in asdict(s):
                if k in data:
                    setattr(s, k, data[k])
        except Exception:
            pass
        # sanitize whatever came from disk
        try:
            s.table_rows_default = max(6, min(30, int(s.table_rows_default)))
        except Exception:
            s.table_rows_default = 12
        if not isinstance(s.export_formats_default, list) or \
                not s.export_formats_default:
            s.export_formats_default = ["png600"]
        s.live_update_default = bool(s.live_update_default)
        s.output_dir_default = str(s.output_dir_default or "")
        return s

    def save(self) -> None:
        p = _settings_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")


def open_preferences_dialog(parent=None):  # pragma: no cover - Qt/display
    """Edit + persist the defaults; returns after Save/Cancel."""
    from PyQt6.QtWidgets import (
        QDialog, QFormLayout, QCheckBox, QSpinBox, QLineEdit, QPushButton,
        QHBoxLayout, QVBoxLayout, QDialogButtonBox, QFileDialog, QGridLayout,
        QWidget, QLabel)
    from metcore_export import ACADEMIC_FORMATS

    s = Settings.load()
    dlg = QDialog(parent)
    dlg.setWindowTitle("Preferences")
    dlg.resize(540, 400)

    form = QFormLayout()
    live = QCheckBox("enabled by default on every panel")
    live.setChecked(s.live_update_default)
    rows = QSpinBox(); rows.setRange(6, 30); rows.setValue(s.table_rows_default)
    out = QLineEdit(s.output_dir_default)
    pick = QPushButton("Folder…"); pick.setMaximumWidth(90)
    pick.clicked.connect(lambda: out.setText(
        QFileDialog.getExistingDirectory(dlg, "Default output folder")
        or out.text()))
    orow = QHBoxLayout(); orow.addWidget(out); orow.addWidget(pick)
    form.addRow("Live update:", live)
    form.addRow("Embedded table rows:", rows)
    form.addRow("Default output folder:", orow)

    root = QVBoxLayout(dlg)
    root.addLayout(form)
    root.addWidget(QLabel("Default export formats:"))
    grid = QGridLayout(); boxes: dict = {}
    for i, (key, ext, _dpi) in enumerate(ACADEMIC_FORMATS):
        cb = QCheckBox(f"{key} (.{ext})")
        cb.setChecked(key in s.export_formats_default)
        boxes[key] = cb
        grid.addWidget(cb, i // 3, i % 3)
    gw = QWidget(); gw.setLayout(grid)
    root.addWidget(gw)

    btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save
                            | QDialogButtonBox.StandardButton.Cancel)

    def _save():
        s.live_update_default = live.isChecked()
        s.table_rows_default = int(rows.value())
        s.output_dir_default = out.text().strip()
        s.export_formats_default = [k for k, cb in boxes.items()
                                    if cb.isChecked()] or ["png600"]
        s.save()
        dlg.accept()
    btns.accepted.connect(_save)
    btns.rejected.connect(dlg.reject)
    root.addWidget(btns)
    dlg.exec()
    return dlg
