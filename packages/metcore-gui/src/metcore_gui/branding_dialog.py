"""Branding editor dialog — wraps the editable fields of
``metcore_export.BrandingConfig`` into a Qt form.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations


def BrandingDialog(parent=None):
    """Factory returning a fresh dialog. Keeps Qt imports lazy so the
    module is importable headlessly."""
    from PyQt6.QtWidgets import (
        QDialog, QFormLayout, QLineEdit, QPushButton, QHBoxLayout,
        QDialogButtonBox, QFileDialog, QComboBox,
    )
    from metcore_export import BrandingConfig

    cfg = BrandingConfig.load()

    dlg = QDialog(parent)
    dlg.setWindowTitle("Branding")
    dlg.resize(520, 380)

    form = QFormLayout()
    institute = QLineEdit(cfg.institute_name)
    institute.setPlaceholderText("(empty = no institute line)")
    inst_clear = QPushButton("\u2715"); inst_clear.setMaximumWidth(30)
    inst_clear.setToolTip("Remove the default text (leave the line blank)")
    inst_clear.clicked.connect(lambda: institute.setText(""))
    inst_row = QHBoxLayout(); inst_row.addWidget(institute); inst_row.addWidget(inst_clear)
    subtitle = QLineEdit(cfg.subtitle)
    reference = QLineEdit(cfg.reference)
    footer = QLineEdit(cfg.footer_text)

    logo = QLineEdit(cfg.logo_path)
    logo.setPlaceholderText('"auto" = sample "Your logo here" - empty = no logo - or a path')
    logo_clear = QPushButton("\u2715"); logo_clear.setMaximumWidth(30)
    logo_clear.setToolTip("Remove the logo (leave empty for none)")
    logo_clear.clicked.connect(lambda: logo.setText(""))
    browse = QPushButton("Browse…")
    browse.setMaximumWidth(100)
    def _browse():
        path, _ = QFileDialog.getOpenFileName(
            dlg, "Choose logo",
            filter="Images (*.png *.jpg *.jpeg *.svg *.ico)")
        if path:
            logo.setText(path)
    browse.clicked.connect(_browse)
    logo_row = QHBoxLayout()
    logo_row.addWidget(logo)
    logo_row.addWidget(browse)
    logo_row.addWidget(logo_clear)

    pos = QComboBox()
    pos.addItems(["left", "right"])
    pos.setCurrentText(cfg.logo_position)

    form.addRow("Institute / lab:",  inst_row)
    form.addRow("Subtitle:",         subtitle)
    form.addRow("Reference (DOI):",  reference)
    form.addRow("Footer text:",      footer)
    form.addRow("Logo path:",        logo_row)
    form.addRow("Logo position:",    pos)

    # ── color theme (academic brand colors) ──
    from metcore_export import THEME_PRESETS
    theme = QComboBox()
    theme.addItem("custom / current")
    for name in THEME_PRESETS:
        theme.addItem(name)
    prim = QLineEdit(cfg.theme_primary)
    prim.setPlaceholderText("#1f4e8c  (curves, table header)")
    seco = QLineEdit(cfg.theme_secondary)
    seco.setPlaceholderText("#c0392b  (fit / comparison lines)")

    def _pick(target, fallback):
        from PyQt6.QtWidgets import QColorDialog
        from PyQt6.QtGui import QColor
        c = QColorDialog.getColor(QColor(target.text().strip() or fallback), dlg)
        if c.isValid():
            target.setText(c.name())
    pick1 = QPushButton("Pick…"); pick1.setMaximumWidth(70)
    pick2 = QPushButton("Pick…"); pick2.setMaximumWidth(70)
    pick1.clicked.connect(lambda: _pick(prim, "#1f4e8c"))
    pick2.clicked.connect(lambda: _pick(seco, "#c0392b"))
    prim_row = QHBoxLayout(); prim_row.addWidget(prim); prim_row.addWidget(pick1)
    seco_row = QHBoxLayout(); seco_row.addWidget(seco); seco_row.addWidget(pick2)

    def _apply_preset(name):
        if name in THEME_PRESETS:
            pcol, scol = THEME_PRESETS[name]
            prim.setText(pcol); seco.setText(scol)
    theme.currentTextChanged.connect(_apply_preset)

    form.addRow("Color theme:",      theme)
    form.addRow("Primary color:",    prim_row)
    form.addRow("Secondary color:",  seco_row)

    btns = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Save
        | QDialogButtonBox.StandardButton.Cancel
    )

    def _save():
        cfg.institute_name = institute.text().strip()
        cfg.subtitle = subtitle.text().strip()
        cfg.reference = reference.text().strip()
        cfg.footer_text = footer.text().strip()
        cfg.logo_path = logo.text().strip()
        cfg.logo_position = pos.currentText()
        cfg.theme_primary = prim.text().strip()
        cfg.theme_secondary = seco.text().strip()
        cfg.save()
        dlg.accept()
    btns.accepted.connect(_save)
    btns.rejected.connect(dlg.reject)

    # Root layout: form + buttons
    from PyQt6.QtWidgets import QVBoxLayout
    root = QVBoxLayout(dlg)
    root.addLayout(form)
    root.addWidget(btns)
    return dlg
