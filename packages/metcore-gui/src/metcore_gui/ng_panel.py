"""
N_G / obliquity panel for the unified Hope 'n Mind GUI.

This is the first concrete ``ModulePanel`` and the reference pattern every
other tool panel follows: a Qt-free *controller* (fully testable headless)
plus a thin Qt *view* that wires inputs to it and renders the figure.

Coherence -> decoherence reading
--------------------------------
The panel plots the Bloch-volume V(t) = |det M(t)| of a qubit channel. For a
Markovian (CP-divisible) channel V(t) decays monotonically: pure decoherence.
When memory is present, V(t) *re-expands* - coherence partially returns - and
the integrated positive part of that re-expansion is exactly N_G. The figure
makes the coherence->decoherence story visible; the number certifies it.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
Author: DESVAUX G.J.Y. - Hope 'n Mind SASU - Research
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

from metcore_gui.panel import ModulePanel

CHANNELS = ("revival", "dephasing", "depolarizing", "amplitude_damping")


# ──────────────────────────────── controller ─────────────────────────────────

@dataclass
class NGResult:
    channel: str
    gamma: float
    omega: Optional[float]
    t: np.ndarray
    volume: np.ndarray            # V(t) = |det M(t)|
    n_g: float
    verdict: str
    meta: dict[str, Any] = field(default_factory=dict)


class NGController:
    """Pure-logic core of the N_G panel. No Qt, no display - unit-testable."""

    def compute(self, channel: str = "revival", gamma: float = 0.1,
                omega: float = 2.0, t_max: float = 12.0,
                n_points: int = 2048) -> NGResult:
        import obliquity_ng as ong

        if channel not in CHANNELS:
            raise ValueError(f"unknown channel {channel!r}; choose from {CHANNELS}")
        if n_points < 16:
            raise ValueError("n_points too small; use >= 16")

        builders = {
            "revival": lambda: ong.nonmarkovian_revival_channel(gamma=gamma, omega=omega),
            "dephasing": lambda: ong.dephasing_channel(gamma),
            "depolarizing": lambda: ong.depolarizing_channel(gamma),
            "amplitude_damping": lambda: ong.amplitude_damping_channel(gamma),
        }
        ch = builders[channel]()
        t = np.linspace(0.0, float(t_max), int(n_points))
        M = ch(t)                                   # (T, 3, 3)
        volume = np.abs(np.linalg.det(M))           # V(t)
        n_g = float(ong.ng_from_bloch_matrices(M, t))
        verdict = ("non-Markovian (memory backflow)" if n_g >= 1e-4
                   else "Markovian (CP-divisible)")
        return NGResult(
            channel=channel, gamma=gamma,
            omega=omega if channel == "revival" else None,
            t=t, volume=volume, n_g=n_g, verdict=verdict,
            meta={"t_max": t_max, "n_points": int(n_points)},
        )

    def make_figure(self, result: NGResult, branding: Any = None):
        """Build a branded matplotlib Figure (no pyplot, no display needed)."""
        from matplotlib.figure import Figure

        fig = Figure(figsize=(7.5, 4.6))
        self.draw_into(fig, result, branding)
        return fig

    def draw_into(self, fig, result: NGResult, branding: Any = None) -> None:
        """Redraw *in place* into an existing Figure (keeps the canvas/DPI).

        Used by the live view so the on-screen canvas is never swapped - that
        swap is what made the redrawn figure render at 1/4 size on HiDPI
        screens. Clearing and repainting the same Figure keeps the device
        pixel ratio the canvas was built with.
        """
        from metcore_export import apply_branding, BrandingConfig, theme_colors

        cfg = branding if branding is not None else BrandingConfig.load()
        th = theme_colors(cfg)
        fig.clear()
        # leave headroom for the branding header
        ax = fig.add_axes([0.12, 0.13, 0.80, 0.66])
        ax.plot(result.t, result.volume, lw=1.6, color=th["primary"])
        ax.fill_between(result.t, result.volume, color=th["fill"], alpha=0.08)
        ax.set_xlabel("time  t")
        ax.set_ylabel(r"Bloch volume  $V(t)=|\det M(t)|$")
        ax.set_ylim(bottom=0.0)
        ax.grid(True, alpha=0.25)
        omega_txt = f", ω={result.omega}" if result.omega is not None else ""
        ax.set_title(
            f"{result.channel}  (γ={result.gamma}{omega_txt})   -   "
            f"N_G = {result.n_g:.4g}   ·   {result.verdict}",
            fontsize=10, pad=8,
        )
        apply_branding(fig, cfg)

    def series(self, result: NGResult):
        """Plotted columns, for CSV / Excel / embedded-table attachments."""
        return [("t", result.t), ("V(t)", result.volume)]

    def export(self, fig, outdir, basename: str = "obliquity_NG",
               branding: Any = None, formats=None):
        """Persist the figure in academic formats via metcore_export."""
        from metcore_export import export_all, BrandingConfig
        # Ensure a savable canvas even on a headless/bare Figure.
        if getattr(fig, "canvas", None) is None or \
                fig.canvas.__class__.__name__ == "FigureCanvasBase":
            from matplotlib.backends.backend_agg import FigureCanvasAgg
            FigureCanvasAgg(fig)
        cfg = branding if branding is not None else BrandingConfig.load()
        return export_all(fig, outdir, basename, branding=cfg, formats=formats,
                          apply=False)  # branding already applied in make_figure


# ─────────────────────────────────── view ────────────────────────────────────

class NGPanel(ModulePanel):
    """Qt tab for geometric non-Markovianity N_G."""

    display_name = "N_G / obliquity"
    description = "Geometric non-Markovianity of a qubit channel (coherence→decoherence)."
    slug = "obliquity-ng"
    domain = "Diagnostics"

    def __init__(self) -> None:
        super().__init__()
        self.ctrl = NGController()
        self._result: Optional[NGResult] = None
        self._fig = None
        self._canvas = None
        self._inputs: dict[str, Any] = {}

    def build(self) -> Any:
        # Qt imported lazily so this module stays headless-importable.
        from PyQt6.QtWidgets import (
            QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox,
            QDoubleSpinBox, QSpinBox, QPushButton, QLabel,
        )
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

        root = QWidget()
        outer = QVBoxLayout(root)

        # --- controls row ---
        form = QFormLayout()
        channel = QComboBox(); channel.addItems(CHANNELS)
        gamma = QDoubleSpinBox(); gamma.setRange(0.001, 100.0); gamma.setValue(0.1); gamma.setSingleStep(0.05)
        omega = QDoubleSpinBox(); omega.setRange(0.0, 100.0); omega.setValue(2.0); omega.setSingleStep(0.1)
        tmax = QDoubleSpinBox(); tmax.setRange(1.0, 1000.0); tmax.setValue(12.0)
        npts = QSpinBox(); npts.setRange(16, 100000); npts.setValue(2048)
        form.addRow("Channel:", channel)
        form.addRow("γ (decay):", gamma)
        form.addRow("ω (revival only):", omega)
        form.addRow("t_max:", tmax)
        form.addRow("points:", npts)
        self._inputs = {"channel": channel, "gamma": gamma, "omega": omega,
                        "tmax": tmax, "npts": npts}

        run_btn = QPushButton("Compute N_G")
        export_btn = QPushButton("Export (branded)…")
        run_btn.clicked.connect(self.on_run)
        export_btn.clicked.connect(self.on_export)
        btn_row = QHBoxLayout(); btn_row.addWidget(run_btn); btn_row.addWidget(export_btn)

        self._status = QLabel("Ready.")

        # --- figure canvas ---
        self._result = self.ctrl.compute()          # initial demo result
        self._fig = self.ctrl.make_figure(self._result)
        self._canvas = FigureCanvasQTAgg(self._fig)

        top = QHBoxLayout(); top.addLayout(form); top.addStretch(1)
        outer.addLayout(top)
        outer.addLayout(btn_row)
        outer.addWidget(self._status)
        outer.addWidget(self._canvas, stretch=1)
        self._widget = root
        from metcore_gui.panel_features import wire_panel_features
        wire_panel_features(self, btn_row)
        return root

    def _read_inputs(self) -> dict[str, Any]:
        i = self._inputs
        return dict(channel=i["channel"].currentText(), gamma=i["gamma"].value(),
                    omega=i["omega"].value(), t_max=i["tmax"].value(),
                    n_points=int(i["npts"].value()))

    def on_run(self) -> None:
        try:
            self._result = self.ctrl.compute(**self._read_inputs())
            from metcore_gui.panel_features import refresh_canvas
            refresh_canvas(self)
            self._status.setText(
                f"N_G = {self._result.n_g:.4g}  ·  {self._result.verdict}")
        except Exception as exc:  # pragma: no cover - UI guard
            self._status.setText(f"Error: {exc}")

    def on_export(self) -> None:  # pragma: no cover - requires display
        from PyQt6.QtWidgets import QFileDialog
        from metcore_gui.branding_dialog import BrandingDialog
        # let the user edit branding first
        dlg = BrandingDialog(self._widget)
        dlg.exec()
        outdir = QFileDialog.getExistingDirectory(self._widget, "Export to folder")
        if not outdir:
            return
        if self._fig is None:
            return
        res = self.ctrl.export(self._fig, outdir,
                               basename=f"NG_{(self._result.channel if self._result else 'demo')}")
        self._status.setText(f"Exported {len(res)} file(s) to {outdir}")

    def export_basename(self) -> str:
        r = getattr(self, "_result", None)
        return f"NG_{r.channel}" if r is not None else "NG"


def make_panel() -> NGPanel:
    """Factory for register_panel / entry-point ``metcore.gui_panels``."""
    return NGPanel()
