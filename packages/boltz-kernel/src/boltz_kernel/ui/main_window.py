"""
BoltZ-Kernel — PyQt6 Desktop GUI
===================================

Desktop application for non-Markovian quantum dynamics simulation.
Researchers can:
  - Select built-in spectral densities OR enter a custom formula
  - Import measured J(ω) from CSV files
  - Adjust all physical parameters
  - Choose an output folder for results
  - Run NM vs Lindblad comparisons
  - Export plots (PNG/PDF/SVG) and data (CSV)

Copyright (c) 2008-2026 Hope 'n Mind SASU - Research — All rights reserved.
Authors: DESVAUX G.J.Y. 
DOI: 10.5281/zenodo.19648837
Contact: contact@hopenmind.com
"""

import sys
import os
import time
import numpy as np

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QComboBox, QDoubleSpinBox, QPushButton,
    QTextEdit, QLineEdit, QSplitter, QStatusBar, QMenuBar,
    QFileDialog, QMessageBox, QProgressBar, QGridLayout,
    QTabWidget, QCheckBox, QSpinBox, QDialog, QDialogButtonBox,
    QFormLayout, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QFont, QIcon

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Resolve base directory (supports both normal and PyInstaller frozen mode)
if getattr(sys, 'frozen', False):
    _BASE = sys._MEIPASS
else:
    _BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')

if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

from core import compare, SpectralDensities, MemoryKernel
from core.lindblad import LindbladSolver
from branding import BrandingConfig


# ─────────────────────────────────────────────────────────
# Worker thread
# ─────────────────────────────────────────────────────────

class SimulationWorker(QThread):
    """Run simulation in background thread."""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, J, g, T, omega0, t_max, dt):
        super().__init__()
        self.J = J
        self.g = g
        self.T = T
        self.omega0 = omega0
        self.t_max = t_max
        self.dt = dt

    def run(self):
        try:
            result = compare(self.J, g=self.g, T=self.T, omega0=self.omega0,
                             t_max=self.t_max, dt=self.dt)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


# ─────────────────────────────────────────────────────────
# Matplotlib canvas
# ─────────────────────────────────────────────────────────

class PlotCanvas(FigureCanvas):
    """
    Embedded matplotlib figure with right-click export context menu.

    Supported academic export formats:
      PNG  — 300 dpi, standard for conference proceedings
      PDF  — vector, for LaTeX / journal submissions
      SVG  — vector, editable in Inkscape / Illustrator
      EPS  — PostScript, required by some legacy journals (AIP, APS)
      TIFF — 600 dpi, required by some biomedical / optics journals
    """

    # Export format definitions: (label, extension, dpi or None for vector)
    _EXPORT_FORMATS = [
        ("PNG  — 300 dpi  (conference / web)",       "png",  300),
        ("PNG  — 600 dpi  (high-res print)",          "png",  600),
        ("PDF  — vector   (LaTeX / journals)",        "pdf",  None),
        ("SVG  — vector   (Inkscape / Illustrator)",  "svg",  None),
        ("EPS  — vector   (AIP, APS legacy journals)","eps",  None),
        ("TIFF — 300 dpi  (standard print)",          "tiff", 300),
        ("TIFF — 600 dpi  (biomedical / optics)",     "tiff", 600),
    ]

    def __init__(self, parent=None, width=10, height=8):
        self.fig = Figure(figsize=(width, height), dpi=100)
        super().__init__(self.fig)
        self.setParent(parent)
        self._last_export_dir = os.path.expanduser("~")
        # Enable right-click
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)

    def contextMenuEvent(self, event):
        """Right-click menu — only shown when a result has been plotted."""
        # Check whether the figure has any subplots (i.e. a result exists)
        if not self.fig.get_axes():
            return

        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setTitle("Export figure")

        title_act = menu.addAction("Export figure as…")
        title_act.setEnabled(False)   # visual header, non-clickable
        menu.addSeparator()

        for label, ext, dpi in self._EXPORT_FORMATS:
            act = menu.addAction(label)
            # Capture loop vars in default args
            act.triggered.connect(
                lambda checked, e=ext, d=dpi, lbl=label: self._export_as(e, d)
            )

        menu.exec(event.globalPos())

    def _export_as(self, ext, dpi):
        """Open save dialog and export figure in the chosen format."""
        fmt_upper = ext.upper()
        dpi_str   = f"_{dpi}dpi" if dpi else "_vector"
        default_name = f"maxent_kernel{dpi_str}.{ext}"
        default_path = os.path.join(self._last_export_dir, default_name)

        # Build filter string
        filter_map = {
            "png":  f"PNG Image (*.png)",
            "pdf":  f"PDF Document (*.pdf)",
            "svg":  f"SVG Vector (*.svg)",
            "eps":  f"EPS PostScript (*.eps)",
            "tiff": f"TIFF Image (*.tiff *.tif)",
        }
        file_filter = filter_map.get(ext, f"{fmt_upper} (*.{ext})")

        path, _ = QFileDialog.getSaveFileName(
            self, f"Export as {fmt_upper}", default_path, file_filter
        )
        if not path:
            return

        self._last_export_dir = os.path.dirname(path)

        try:
            import matplotlib
            save_kwargs = {"bbox_inches": "tight", "facecolor": "white"}
            if dpi:
                save_kwargs["dpi"] = dpi

            # Embed hidden metadata — filtered per format
            branding = getattr(self, '_branding', None)
            if branding is not None:
                meta = branding.metadata_for_format(ext)
                if meta is not None:
                    save_kwargs["metadata"] = meta

            # EPS / PS: force Type 42 fonts (TrueType wrapper) so Inkscape,
            # Illustrator and ghostscript can handle them without crashing.
            # Type 3 (matplotlib default) causes Inkscape to close silently.
            _prev_fonttype = matplotlib.rcParams.get('ps.fonttype', 3)
            if ext == "eps":
                matplotlib.rcParams['ps.fonttype'] = 42

            self.fig.savefig(path, **save_kwargs)

            # Restore font type setting
            if ext == "eps":
                matplotlib.rcParams['ps.fonttype'] = _prev_fonttype

        except Exception as e:
            QMessageBox.warning(
                self, "Export Error",
                f"Could not save figure:\n{e}"
            )

    def plot_result(self, result, branding=None, source_label=None):
        self._branding = branding  # keep ref for context-menu export metadata
        self.fig.clear()

        # Apply branding (header, source label, footer, optional logo)
        if branding is not None:
            _logo_default = os.path.join(os.path.dirname(__file__), 'assets', 'logo.png')
            if getattr(sys, 'frozen', False):
                _logo_default = os.path.join(sys._MEIPASS, 'ui', 'assets', 'logo.png')
            branding.apply_to_figure(
                self.fig,
                _default_logo_path=_logo_default,
                source_label=source_label
            )
        else:
            self.fig.suptitle(
                "Non-Markovian vs Lindblad Dynamics\n"
                "Hope 'n Mind SASU - Research — DOI: 10.5281/zenodo.19648837",
                fontsize=11, fontweight='bold'
            )
            if source_label:
                self.fig.text(
                    0.01, 0.895, f"J(\u03c9): {source_label}",
                    ha='left', va='top',
                    fontsize=7.5, color='#444444', style='italic'
                )

        ax1 = self.fig.add_subplot(221)
        ax1.plot(result.t, result.nm.populations, 'b-', lw=2, label='Non-Markovian')
        ax1.plot(result.t, result.markov.populations, 'r--', lw=2, label='Lindblad')
        ax1.set_xlabel('Time')
        ax1.set_ylabel('P_e(t)')
        ax1.set_title('Excited State Population')
        ax1.legend(fontsize=8)
        ax1.grid(True, alpha=0.3)

        ax2 = self.fig.add_subplot(222)
        ax2.plot(result.t, result.nm.coherences, 'b-', lw=2, label='Non-Markovian')
        ax2.plot(result.t, result.markov.coherences, 'r--', lw=2, label='Lindblad')
        ax2.set_xlabel('Time')
        ax2.set_ylabel('|ρ₀₁(t)|')
        ax2.set_title('Coherence')
        ax2.legend(fontsize=8)
        ax2.grid(True, alpha=0.3)

        ax3 = self.fig.add_subplot(223)
        td = result.trace_distance
        ax3.plot(result.t, td, 'k-', lw=2)
        ax3.axhline(0.01, color='orange', ls='--', label='1% threshold')
        ax3.fill_between(result.t, 0, td, alpha=0.2, color='purple')
        ax3.set_xlabel('Time')
        ax3.set_ylabel('D(ρ_NM, ρ_M)')
        ax3.set_title(f'Trace Distance — Max: {result.max_deviation:.4f}')
        ax3.legend(fontsize=8)
        ax3.grid(True, alpha=0.3)

        ax4 = self.fig.add_subplot(224)
        t_mid = result.kernel.t_max / 2
        s_vals, K_vals = result.kernel.kernel_at(t_mid)
        if len(s_vals) > 1:
            lags = t_mid - s_vals
            ax4.plot(lags, K_vals, 'g-', lw=2)
            ax4.set_xlabel('Lag (t - s)')
            ax4.set_ylabel('K*(t, s)')
            ax4.set_title(f'Memory Kernel at t={t_mid:.1f}')
        else:
            ax4.text(0.5, 0.5, 'Kernel too short', ha='center', va='center',
                     transform=ax4.transAxes)
        ax4.grid(True, alpha=0.3)

        self.fig.tight_layout(rect=[0, 0.03, 1, 0.93])
        self.draw()

    def save_figure(self, path, branding=None):
        kwargs = {"dpi": 150, "bbox_inches": "tight", "facecolor": "white"}
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        if branding is not None:
            meta = branding.metadata_for_format(ext)
            if meta is not None:
                kwargs["metadata"] = meta
        self.fig.savefig(path, **kwargs)


# ─────────────────────────────────────────────────────────
# CSV interpolation helper
# ─────────────────────────────────────────────────────────

def load_csv_spectral_density(filepath):
    """
    Load a measured spectral density from a CSV file.

    Expected format:
        omega,J
        0.1,0.003
        0.2,0.012
        ...

    First column = frequency (omega), second column = J(omega).
    Returns a callable J(omega) via linear interpolation.
    """
    from scipy.interpolate import interp1d

    data = np.genfromtxt(filepath, delimiter=',', skip_header=1)
    if data.ndim == 1:
        # Try tab or space separation
        data = np.genfromtxt(filepath, skip_header=1)
    if data.ndim == 1 or data.shape[1] < 2:
        raise ValueError(
            "CSV must have 2 columns: omega, J(omega).\n"
            "Accepted separators: comma, tab, space.\n"
            "First row is treated as header and skipped."
        )

    omega = data[:, 0]
    J_vals = data[:, 1]

    J_interp = interp1d(omega, J_vals, kind='linear',
                         fill_value=0.0, bounds_error=False)

    def J(w):
        return float(J_interp(w))

    J.__doc__ = f"CSV: {os.path.basename(filepath)} ({len(omega)} points)"
    return J


# ─────────────────────────────────────────────────────────
# Built-in spectral densities
# ─────────────────────────────────────────────────────────

BUILTIN_SD = {
    "Ohmic (generic bath)":          lambda: SpectralDensities.ohmic(eta=0.1, wc=10.0, s=1),
    "Super-Ohmic (s=3)":             lambda: SpectralDensities.ohmic(eta=0.01, wc=10.0, s=3),
    "Lorentzian (cavity)":           lambda: SpectralDensities.lorentzian(gamma=0.5, wc=5.0, width=0.3),
    "Band Edge (photonic crystal)":  lambda: SpectralDensities.band_edge(beta=0.05, we=5.0),
    "Photonic Crystal (with gap)":   lambda: SpectralDensities.photonic_crystal(beta=0.05, we=5.0, gap_width=2.0),
    "Waveguide QED (mirror)":        lambda: SpectralDensities.waveguide(gamma_1d=0.5, tau_rt=1.0, r=0.9),
}


# ─────────────────────────────────────────────────────────
# Header Settings Dialog
# ─────────────────────────────────────────────────────────

class HeaderSettingsDialog(QDialog):
    """
    Dialog to customize every visible field on plots and summary files.

    Layout (top-to-bottom, mirrors the figure):
      1. Institute / Group name   — bold, top line
      2. Subtitle                 — second line (authors, experiment, …)
      3. Reference field          — third line (DOI, arXiv, grant, …)
      4. Logo path + Left / Right placement
      5. Footer text              — centered, small, bottom of figure

    Hope 'n Mind / BoltZ-Kernel identity is silently embedded in
    file metadata on every export — not shown on the figure.
    """

    def __init__(self, branding: BrandingConfig, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Header Settings")
        self.setMinimumWidth(560)
        self._branding = branding

        from PyQt6.QtWidgets import QRadioButton, QButtonGroup
        layout = QVBoxLayout(self)

        # ── Header fields ────────────────────────────────────────────────────
        header_group = QGroupBox("Figure header  (top of plot)")
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setVerticalSpacing(10)

        self.name_edit = QLineEdit(branding.institute_name)
        self.name_edit.setPlaceholderText("e.g. Quantum Optics Lab — University of Paris")
        self.name_edit.setFont(QFont("", 0, QFont.Weight.Bold))
        form.addRow("Institute / Group name:", self.name_edit)

        self.subtitle_edit = QLineEdit(branding.subtitle)
        self.subtitle_edit.setPlaceholderText(
            "e.g. Non-Markovian vs Lindblad Dynamics  or  Author A, Author B"
        )
        form.addRow("Subtitle / Authors:", self.subtitle_edit)

        self.ref_edit = QLineEdit(branding.reference)
        self.ref_edit.setPlaceholderText(
            "e.g. DOI: 10.5281/zenodo.19648837  or  arXiv:2401.00001"
        )
        form.addRow("Reference field:", self.ref_edit)

        header_group.setLayout(form)
        layout.addWidget(header_group)

        # ── Logo ─────────────────────────────────────────────────────────────
        logo_group = QGroupBox("Logo")
        logo_layout = QVBoxLayout()

        logo_path_row = QHBoxLayout()
        self.logo_edit = QLineEdit(branding.logo_path)
        self.logo_edit.setPlaceholderText("Leave empty to use the BoltZ-Kernel logo")
        logo_browse = QPushButton("Browse…")
        logo_browse.setMaximumWidth(80)
        logo_browse.clicked.connect(self._browse_logo)
        logo_path_row.addWidget(self.logo_edit)
        logo_path_row.addWidget(logo_browse)
        logo_layout.addLayout(logo_path_row)

        logo_pos_row = QHBoxLayout()
        logo_pos_row.addWidget(QLabel("Position:"))
        self._logo_left  = QRadioButton("Left")
        self._logo_right = QRadioButton("Right")
        self._logo_group = QButtonGroup(self)
        self._logo_group.addButton(self._logo_left,  0)
        self._logo_group.addButton(self._logo_right, 1)
        (self._logo_left if branding.logo_position != "right" else self._logo_right).setChecked(True)
        logo_pos_row.addWidget(self._logo_left)
        logo_pos_row.addWidget(self._logo_right)
        logo_pos_row.addStretch()
        logo_layout.addLayout(logo_pos_row)

        logo_group.setLayout(logo_layout)
        layout.addWidget(logo_group)

        # ── Footer ───────────────────────────────────────────────────────────
        footer_group = QGroupBox("Footer  (centered, bottom of figure)")
        footer_layout = QVBoxLayout()
        self.footer_edit = QLineEdit(branding.footer_text)
        self.footer_edit.setPlaceholderText(
            "e.g. BoltZ-Kernel solver by Hope 'n Mind SASU - Research"
        )
        self.footer_edit.setStyleSheet("color: #555555; font-style: italic;")
        footer_layout.addWidget(self.footer_edit)
        footer_group.setLayout(footer_layout)
        layout.addWidget(footer_group)

        # ── Separator + buttons ──────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        btn_box = QDialogButtonBox()
        save_btn   = btn_box.addButton("Save",             QDialogButtonBox.ButtonRole.AcceptRole)
        reset_btn  = btn_box.addButton("Reset to Default", QDialogButtonBox.ButtonRole.ResetRole)
        cancel_btn = btn_box.addButton("Cancel",           QDialogButtonBox.ButtonRole.RejectRole)

        save_btn.clicked.connect(self._save)
        reset_btn.clicked.connect(self._reset)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(btn_box)

    def _browse_logo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Logo Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All files (*)"
        )
        if path:
            self.logo_edit.setText(path)

    def _save(self):
        self._branding.institute_name = self.name_edit.text().strip()
        self._branding.subtitle       = self.subtitle_edit.text().strip()
        self._branding.reference      = self.ref_edit.text().strip()
        self._branding.logo_path      = self.logo_edit.text().strip()
        self._branding.logo_position  = "right" if self._logo_right.isChecked() else "left"
        self._branding.footer_text    = self.footer_edit.text().strip()
        try:
            self._branding.save()
        except Exception as e:
            QMessageBox.warning(self, "Save Error", f"Could not save settings:\n{e}")
            return
        self.accept()

    def _reset(self):
        self._branding.reset_to_defaults()
        self.name_edit.setText(self._branding.institute_name)
        self.subtitle_edit.setText(self._branding.subtitle)
        self.ref_edit.setText(self._branding.reference)
        self.logo_edit.setText(self._branding.logo_path)
        self._logo_left.setChecked(True)
        self.footer_edit.setText(self._branding.footer_text)


# ─────────────────────────────────────────────────────────
# Main Window
# ─────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    """BoltZ-Kernel main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("BoltZ-Kernel — Non-Markovian Quantum Solver")
        self.setMinimumSize(1280, 800)

        # Set window & taskbar icon
        icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'logo.png')
        if getattr(sys, 'frozen', False):
            icon_path = os.path.join(sys._MEIPASS, 'ui', 'assets', 'logo.png')
        if os.path.isfile(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.result = None
        self.worker = None
        self.csv_J = None
        self.branding = BrandingConfig.load()
        self.output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'Results')
        self.output_dir = os.path.abspath(self.output_dir)

        self._build_menu()
        self._build_ui()
        self._build_statusbar()

    # ── Menu ──

    def _build_menu(self):
        menubar = self.menuBar()

        # File
        file_menu = menubar.addMenu("&File")

        import_act = QAction("&Import CSV J(ω)...", self)
        import_act.setShortcut("Ctrl+I")
        import_act.triggered.connect(self._import_csv)
        file_menu.addAction(import_act)

        file_menu.addSeparator()

        save_act = QAction("&Save Plot...", self)
        save_act.setShortcut("Ctrl+S")
        save_act.triggered.connect(self._save_plot)
        file_menu.addAction(save_act)

        export_act = QAction("&Export Data (CSV)...", self)
        export_act.setShortcut("Ctrl+E")
        export_act.triggered.connect(self._export_data)
        file_menu.addAction(export_act)

        file_menu.addSeparator()

        outdir_act = QAction("Set &Output Folder...", self)
        outdir_act.triggered.connect(self._set_output_dir)
        file_menu.addAction(outdir_act)

        file_menu.addSeparator()

        quit_act = QAction("&Quit", self)
        quit_act.setShortcut("Ctrl+Q")
        quit_act.triggered.connect(self.close)
        file_menu.addAction(quit_act)

        # Edit
        edit_menu = menubar.addMenu("&Edit")

        header_act = QAction("&Header Settings…", self)
        header_act.setShortcut("Ctrl+H")
        header_act.setStatusTip("Customize the institute name, logo and DOI on outputs")
        header_act.triggered.connect(self._show_header_settings)
        edit_menu.addAction(header_act)

        # Help
        help_menu = menubar.addMenu("&Help")

        guide_act = QAction("&User Guide", self)
        guide_act.triggered.connect(self._show_guide)
        help_menu.addAction(guide_act)

        about_act = QAction("&About", self)
        about_act.triggered.connect(self._show_about)
        help_menu.addAction(about_act)

    # ── UI ──

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        # ── Left panel ──
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setMaximumWidth(420)

        # --- Tab widget for data source ---
        self.source_tabs = QTabWidget()

        # Tab 1: Built-in spectral densities
        tab_builtin = QWidget()
        tab_bl = QVBoxLayout(tab_builtin)
        self.sd_combo = QComboBox()
        for name in BUILTIN_SD:
            self.sd_combo.addItem(name)
        tab_bl.addWidget(QLabel("Select a pre-defined spectral density:"))
        tab_bl.addWidget(self.sd_combo)
        tab_bl.addStretch()
        self.source_tabs.addTab(tab_builtin, "Built-in J(ω)")

        # Tab 2: Custom formula
        tab_custom = QWidget()
        tab_cl = QVBoxLayout(tab_custom)
        tab_cl.addWidget(QLabel("Enter your spectral density as a Python expression:"))
        tab_cl.addWidget(QLabel("Variable: w (frequency). Use numpy as np."))
        self.formula_input = QLineEdit()
        self.formula_input.setPlaceholderText("e.g.  0.1 * w**2 * np.exp(-w / 8)")
        self.formula_input.setFont(QFont("Consolas", 11))
        tab_cl.addWidget(self.formula_input)
        tab_cl.addWidget(QLabel(
            "Examples:\n"
            "  0.1 * w * np.exp(-w/10)           — Ohmic\n"
            "  0.5 * 0.3**2 / ((w-5)**2 + 0.3**2) — Lorentzian\n"
            "  0.05**1.5 / np.sqrt(w - 5) if w > 5 else 0  — Band edge"
        ))
        tab_cl.addStretch()
        self.source_tabs.addTab(tab_custom, "Custom Formula")

        # Tab 3: CSV import
        tab_csv = QWidget()
        tab_csvl = QVBoxLayout(tab_csv)
        tab_csvl.addWidget(QLabel("Import measured J(ω) from a CSV file:"))
        tab_csvl.addWidget(QLabel(
            "Format: 2 columns (omega, J), comma/tab/space separated.\n"
            "First row = header (skipped)."
        ))
        csv_row = QHBoxLayout()
        self.csv_path_label = QLabel("No file loaded")
        self.csv_path_label.setStyleSheet("color: #666;")
        csv_btn = QPushButton("Browse...")
        csv_btn.clicked.connect(self._import_csv)
        csv_row.addWidget(self.csv_path_label, stretch=1)
        csv_row.addWidget(csv_btn)
        tab_csvl.addLayout(csv_row)
        self.csv_points_label = QLabel("")
        tab_csvl.addWidget(self.csv_points_label)
        tab_csvl.addStretch()
        self.source_tabs.addTab(tab_csv, "CSV Data")

        left_layout.addWidget(self.source_tabs)

        # --- Physical parameters ---
        param_group = QGroupBox("Physical Parameters")
        param_grid = QGridLayout()

        self.spin_g = self._make_spin(0.001, 10.0, 0.3, 3, "Coupling constant g")
        self.spin_T = self._make_spin(0.0001, 10.0, 0.1, 4, "Effective temperature T (ℏ=k_B=1)")
        self.spin_omega0 = self._make_spin(0.01, 100.0, 5.0, 2, "Emitter transition frequency ω₀")
        self.spin_tmax = self._make_spin(1.0, 500.0, 30.0, 1, "Maximum simulation time")
        self.spin_dt = self._make_spin(0.01, 5.0, 0.2, 2, "Time step (smaller = more accurate but slower)")

        params = [
            ("Coupling g:", self.spin_g),
            ("Temperature T:", self.spin_T),
            ("Frequency ω₀:", self.spin_omega0),
            ("Max time:", self.spin_tmax),
            ("Time step dt:", self.spin_dt),
        ]
        for row, (label, spin) in enumerate(params):
            param_grid.addWidget(QLabel(label), row, 0)
            param_grid.addWidget(spin, row, 1)

        param_group.setLayout(param_grid)
        left_layout.addWidget(param_group)

        # --- Output folder ---
        out_group = QGroupBox("Output Folder")
        out_layout = QHBoxLayout()
        self.outdir_label = QLabel(self._short_path(self.output_dir))
        self.outdir_label.setToolTip(self.output_dir)
        out_btn = QPushButton("Change...")
        out_btn.clicked.connect(self._set_output_dir)
        out_layout.addWidget(self.outdir_label, stretch=1)
        out_layout.addWidget(out_btn)
        out_group.setLayout(out_layout)
        left_layout.addWidget(out_group)

        # --- Auto-save checkbox ---
        self.auto_save_cb = QCheckBox("Auto-save plot + CSV after each run")
        self.auto_save_cb.setChecked(True)
        left_layout.addWidget(self.auto_save_cb)

        # --- Run button ---
        self.run_btn = QPushButton("▶  Run Comparison")
        self.run_btn.setStyleSheet(
            "QPushButton { background-color: #2563eb; color: white; "
            "font-weight: bold; padding: 12px; border-radius: 5px; font-size: 14px; }"
            "QPushButton:hover { background-color: #1d4ed8; }"
            "QPushButton:disabled { background-color: #94a3b8; }"
        )
        self.run_btn.clicked.connect(self._run_simulation)
        left_layout.addWidget(self.run_btn)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        left_layout.addWidget(self.progress)

        # --- Results text ---
        result_group = QGroupBox("Results")
        result_layout = QVBoxLayout()
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFont(QFont("Consolas", 10))
        self.result_text.setMaximumHeight(220)
        result_layout.addWidget(self.result_text)
        result_group.setLayout(result_layout)
        left_layout.addWidget(result_group)

        left_layout.addStretch()

        # ── Right panel: plot ──
        self.canvas = PlotCanvas(width=9, height=7)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(self.canvas)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter)

    def _build_statusbar(self):
        self.statusBar().showMessage(
            f"Hope 'n Mind SASU - Research — BoltZ-Kernel v1.0.0 — Output: {self.output_dir}"
        )

    def _make_spin(self, vmin, vmax, default, decimals, tooltip):
        spin = QDoubleSpinBox()
        spin.setRange(vmin, vmax)
        spin.setValue(default)
        spin.setDecimals(decimals)
        spin.setSingleStep(10 ** (-decimals))
        spin.setToolTip(tooltip)
        return spin

    def _short_path(self, path):
        """Shorten path for display."""
        if len(path) > 45:
            return "..." + path[-42:]
        return path

    # ── Build spectral density from current tab ──

    def _get_spectral_density(self):
        """
        Return a callable J(omega) based on the active tab.
        Raises ValueError with user-facing message if input is invalid.
        """
        tab_idx = self.source_tabs.currentIndex()

        if tab_idx == 0:
            # Built-in
            name = self.sd_combo.currentText()
            return BUILTIN_SD[name](), name

        elif tab_idx == 1:
            # Custom formula
            formula = self.formula_input.text().strip()
            if not formula:
                raise ValueError("Please enter a formula for J(ω).")

            # Build safe callable
            def J(w):
                try:
                    return float(eval(formula, {"__builtins__": {}},
                                      {"w": w, "np": np, "pi": np.pi,
                                       "exp": np.exp, "sqrt": np.sqrt,
                                       "sin": np.sin, "cos": np.cos,
                                       "log": np.log, "abs": abs}))
                except Exception:
                    return 0.0

            # Test it
            test_val = J(1.0)
            if not np.isfinite(test_val):
                raise ValueError(f"Formula returned non-finite at ω=1: {test_val}")

            return J, f"Custom: {formula[:40]}"

        elif tab_idx == 2:
            # CSV
            if self.csv_J is None:
                raise ValueError(
                    "No CSV file loaded.\n\n"
                    "Click 'Browse...' to load a file with 2 columns:\n"
                    "  omega, J(omega)\n\n"
                    "Example:\n"
                    "  omega,J\n"
                    "  0.1,0.003\n"
                    "  0.2,0.012\n"
                    "  ..."
                )
            return self.csv_J, f"CSV data"

        raise ValueError("Unknown data source tab.")

    # ── Actions ──

    def _run_simulation(self):
        try:
            J, source_name = self._get_spectral_density()
        except ValueError as e:
            QMessageBox.warning(self, "Input Error", str(e))
            return

        g = self.spin_g.value()
        T = self.spin_T.value()
        omega0 = self.spin_omega0.value()
        t_max = self.spin_tmax.value()
        dt = self.spin_dt.value()

        self.run_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.result_text.setPlainText(f"Computing ({source_name})...")
        self.statusBar().showMessage("Simulation running...")
        self._current_source_name = source_name

        self.worker = SimulationWorker(J, g, T, omega0, t_max, dt)
        self.worker.finished.connect(self._on_result)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_result(self, result):
        self.result = result
        self.canvas.plot_result(
            result,
            branding=self.branding,
            source_label=getattr(self, '_current_source_name', None)
        )
        self.result_text.setPlainText(result.summary())
        self.run_btn.setEnabled(True)
        self.progress.setVisible(False)

        # Auto-save if enabled
        if self.auto_save_cb.isChecked():
            self._auto_save(result)

        self.statusBar().showMessage(
            f"Done — {result.regime} | Max ΔD = {result.max_deviation:.4f} | "
            f"Output: {self.output_dir}"
        )

    def _on_error(self, msg):
        self.run_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.result_text.setPlainText(f"ERROR: {msg}")
        self.statusBar().showMessage("Simulation failed.")

    def _auto_save(self, result):
        """Auto-save plot and CSV to output folder."""
        os.makedirs(self.output_dir, exist_ok=True)
        self.canvas._last_export_dir = self.output_dir  # keep right-click in sync
        timestamp = time.strftime("%Y%m%d_%H%M%S")

        # Save plot (with hidden metadata)
        plot_path = os.path.join(self.output_dir, f"comparison_{timestamp}.png")
        self.canvas.save_figure(plot_path, branding=self.branding)

        # Save CSV
        csv_path = os.path.join(self.output_dir, f"data_{timestamp}.csv")
        t = result.t
        nm_pop = result.nm.populations
        m_pop = result.markov.populations
        nm_coh = result.nm.coherences
        m_coh = result.markov.coherences
        td = result.trace_distance
        header = "time,P_e_NM,P_e_Lindblad,coherence_NM,coherence_Lindblad,trace_distance"
        data = np.column_stack([t, nm_pop, m_pop, nm_coh, m_coh, td])
        np.savetxt(csv_path, data, delimiter=',', header=header, comments='')

        # Save summary
        summary_path = os.path.join(self.output_dir, f"summary_{timestamp}.txt")
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(self.branding.summary_header())
            f.write("\n\n")
            f.write(result.summary())
            f.write(f"\n\nSource: {getattr(self, '_current_source_name', 'N/A')}\n")
            f.write(f"Parameters: g={self.spin_g.value()}, T={self.spin_T.value()}, "
                    f"omega0={self.spin_omega0.value()}, t_max={self.spin_tmax.value()}, "
                    f"dt={self.spin_dt.value()}\n")
            f.write(f"\nFiles:\n  Plot: {plot_path}\n  Data: {csv_path}\n")
            if self.branding.footer_text:
                f.write(f"\n{self.branding.footer_text}\n")

        self.result_text.append(
            f"\n--- Auto-saved to {self.output_dir} ---\n"
            f"  Plot:    comparison_{timestamp}.png\n"
            f"  Data:    data_{timestamp}.csv\n"
            f"  Summary: summary_{timestamp}.txt"
        )

    def _import_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Spectral Density CSV", "",
            "CSV files (*.csv *.txt *.dat);;All files (*)"
        )
        if not path:
            return
        try:
            self.csv_J = load_csv_spectral_density(path)
            fname = os.path.basename(path)
            self.csv_path_label.setText(fname)
            self.csv_path_label.setStyleSheet("color: #16a34a; font-weight: bold;")
            # Count points
            data = np.genfromtxt(path, delimiter=',', skip_header=1)
            if data.ndim == 1:
                data = np.genfromtxt(path, skip_header=1)
            n_pts = data.shape[0] if data.ndim > 1 else 1
            self.csv_points_label.setText(f"Loaded: {n_pts} data points")
            self.csv_points_label.setStyleSheet("color: #16a34a;")
            # Switch to CSV tab
            self.source_tabs.setCurrentIndex(2)
            self.statusBar().showMessage(f"CSV loaded: {fname} ({n_pts} points)")
        except Exception as e:
            QMessageBox.warning(self, "CSV Import Error", str(e))

    def _save_plot(self):
        if self.result is None:
            QMessageBox.information(self, "No data", "Run a simulation first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Plot", os.path.join(self.output_dir, "comparison.png"),
            "PNG (*.png);;PDF (*.pdf);;SVG (*.svg)"
        )
        if path:
            self.canvas.save_figure(path, branding=self.branding)
            self.statusBar().showMessage(f"Plot saved: {path}")

    def _export_data(self):
        if self.result is None:
            QMessageBox.information(self, "No data", "Run a simulation first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Data", os.path.join(self.output_dir, "data.csv"),
            "CSV (*.csv)"
        )
        if path:
            t = self.result.t
            nm_pop = self.result.nm.populations
            m_pop = self.result.markov.populations
            nm_coh = self.result.nm.coherences
            m_coh = self.result.markov.coherences
            td = self.result.trace_distance
            header = "time,P_e_NM,P_e_Lindblad,coherence_NM,coherence_Lindblad,trace_distance"
            data = np.column_stack([t, nm_pop, m_pop, nm_coh, m_coh, td])
            np.savetxt(path, data, delimiter=',', header=header, comments='')
            self.statusBar().showMessage(f"Data exported: {path}")

    def _set_output_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Select Output Folder", self.output_dir)
        if d:
            self.output_dir = d
            self.canvas._last_export_dir = d   # keep right-click export in sync
            self.outdir_label.setText(self._short_path(d))
            self.outdir_label.setToolTip(d)
            self.statusBar().showMessage(f"Output folder: {d}")

    def _show_header_settings(self):
        """Open the Header Settings dialog (Edit menu)."""
        dlg = HeaderSettingsDialog(self.branding, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            # Branding already mutated and saved inside the dialog.
            # Re-render the current plot if one exists.
            if self.result is not None:
                self.canvas.plot_result(
                    self.result,
                    branding=self.branding,
                    source_label=getattr(self, '_current_source_name', None)
                )
            self.statusBar().showMessage(
                f"Header updated — {self.branding.institute_name}"
            )

    def _show_guide(self):
        QMessageBox.information(
            self,
            "User Guide — BoltZ-Kernel",
            "<h3>How to use BoltZ-Kernel</h3>"
            "<h4>1. Choose your spectral density</h4>"
            "<p><b>Built-in:</b> Select a preset from the dropdown (Ohmic, Lorentzian, etc.)</p>"
            "<p><b>Custom formula:</b> Type a Python expression using <code>w</code> as the "
            "frequency variable. Example: <code>0.1 * w * np.exp(-w/10)</code></p>"
            "<p><b>CSV data:</b> Import a file with 2 columns: omega and J(omega). "
            "The solver interpolates linearly between your data points.</p>"
            "<h4>2. Set physical parameters</h4>"
            "<p>Adjust coupling g, temperature T, emitter frequency ω₀, "
            "simulation time t_max, and time step dt.</p>"
            "<h4>3. Run the comparison</h4>"
            "<p>Click <b>Run Comparison</b>. The solver computes both non-Markovian "
            "(Boltzmann kernel) and Lindblad (Markovian) dynamics.</p>"
            "<h4>4. Collect results</h4>"
            "<p>If auto-save is enabled, three files are written to the output folder "
            "after each run:</p>"
            "<ul>"
            "<li><b>comparison_TIMESTAMP.png</b> — 4-panel plot</li>"
            "<li><b>data_TIMESTAMP.csv</b> — full time series</li>"
            "<li><b>summary_TIMESTAMP.txt</b> — regime, parameters, metrics</li>"
            "</ul>"
            "<p>You can also manually save plots (Ctrl+S) and export data (Ctrl+E) "
            "to any location.</p>"
            "<h4>5. Interpret</h4>"
            "<p>If <b>max trace distance &lt; 0.01</b>: Lindblad is valid for your system.<br>"
            "If <b>memory parameter P &gt; 1</b>: strongly non-Markovian regime.</p>"
        )

    def _show_about(self):
        QMessageBox.about(
            self,
            "About BoltZ-Kernel",
            "<h3>BoltZ-Kernel v1.0.0</h3>"
            "<p>Non-Markovian Quantum Dynamics Solver<br>"
            "with Boltzmann Memory Kernel</p>"
            "<p><b>Authors:</b> DESVAUX G.J.Y. et al.</p>"
            "<p><b>DOI:</b> <a href='https://doi.org/10.5281/zenodo.19648837'>"
            "10.5281/zenodo.19648837</a></p>"
            "<p><b>License:</b> Proprietary — Scientific license on request</p>"
            "<p><b>Contact:</b> contact@hopenmind.com</p>"
            "<hr>"
            "<p>&copy; 2008-2026 Hope 'n Mind SASU - Research — All rights reserved.</p>"
        )


# ─────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("BoltZ-Kernel")
    app.setOrganizationName("Hope 'n Mind SASU - Research")
    app.setStyle("Fusion")

    # App-level icon (taskbar grouping on Windows)
    icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'logo.png')
    if getattr(sys, 'frozen', False):
        icon_path = os.path.join(sys._MEIPASS, 'ui', 'assets', 'logo.png')
    if os.path.isfile(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
