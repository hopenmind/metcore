"""
Rheology adapter panel - the Classical & Rheology specialty tab.

Demonstrates the domain-adapter pattern: viscoelastic relaxation modulus
G(t) = Σ g_i e^{-t/τ_i} is *literally* a Prony series, so the same MET engine
that compiles quantum bath kernels compiles a rheological modulus with no change
- only the input/output vocabulary differs (moduli & relaxation times instead of
amplitudes & rates). Controller is Qt-free and unit-tested; the view is thin.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
Author: DESVAUX G.J.Y. - Hope 'n Mind SASU - Research
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

from metcore_gui.panel import ModulePanel


@dataclass
class RheologyResult:
    t: np.ndarray
    G: np.ndarray
    G_fit: np.ndarray
    moduli: np.ndarray            # g_i  (Prony amplitudes)
    relax_times: np.ndarray       # τ_i = 1/β_i  (relaxation spectrum)
    n_modes: int
    rms_error: float
    regime: str


class RheologyController:
    """Compile a relaxation modulus G(t) into a Maxwell-Wiechert (Prony) spectrum."""

    def compute_from_modes(self, moduli, times, t_max: float = 10.0,
                           n_points: int = 400) -> RheologyResult:
        from memkern import prony_decompose, embeddability_report
        g = np.asarray(moduli, dtype=float)
        tau = np.asarray(times, dtype=float)
        t = np.linspace(0.0, float(t_max), int(n_points))
        G = (g[None, :] * np.exp(-t[:, None] / tau[None, :])).sum(axis=1)
        return self.compute_from_curve(t, G)

    def compute_from_curve(self, t, G) -> RheologyResult:
        from memkern import prony_decompose, embeddability_report
        t = np.asarray(t, dtype=float)
        G = np.asarray(G, dtype=float)
        emb = embeddability_report(t, G)
        K = int(emb.get("K_est", 1))
        res = prony_decompose(t, G.astype(complex), n_exp=K)
        g_i = np.real(res.alphas)
        tau_i = np.real(1.0 / res.betas)
        fit = np.real(res.evaluate(t))
        rms = float(np.sqrt(np.mean((fit - G) ** 2)))
        return RheologyResult(t=t, G=G, G_fit=fit, moduli=g_i, relax_times=tau_i,
                              n_modes=int(res.n_exp), rms_error=rms,
                              regime=emb.get("regime", "unknown"))

    def make_figure(self, r: RheologyResult, branding: Any = None):
        from matplotlib.figure import Figure
        fig = Figure(figsize=(7.5, 4.6))
        self.draw_into(fig, r, branding)
        return fig

    def draw_into(self, fig, r: RheologyResult, branding: Any = None) -> None:
        """Redraw in place (keeps the canvas DPI; no figure swap)."""
        from metcore_export import apply_branding, BrandingConfig, theme_colors
        cfg = branding if branding is not None else BrandingConfig.load()
        th = theme_colors(cfg)
        fig.clear()
        ax = fig.add_axes([0.12, 0.13, 0.80, 0.66])
        ax.plot(r.t, r.G, lw=2.0, color=th["primary"], label="G(t) data")
        ax.plot(r.t, r.G_fit, "--", lw=1.3, color=th["secondary"], label="Prony fit")
        ax.set_xlabel("time  t"); ax.set_ylabel("relaxation modulus  G(t)")
        ax.legend(loc="upper right", fontsize=8); ax.grid(True, alpha=0.25)
        ax.set_title(f"Maxwell-Wiechert spectrum - {r.n_modes} modes "
                     f"(rms {r.rms_error:.2g}, {r.regime})", fontsize=10, pad=8)
        apply_branding(fig, cfg)

    def series(self, r: RheologyResult):
        return [("t", r.t), ("G", r.G), ("G_fit", r.G_fit)]


class RheologyPanel(ModulePanel):
    display_name = "Rheology G(t)"
    description = "Maxwell-Wiechert / Prony relaxation spectrum of a modulus G(t)."
    slug = "memkern-rheology"
    domain = "Classical & Rheology"

    def __init__(self) -> None:
        super().__init__()
        self.ctrl = RheologyController()
        self._result: Optional[RheologyResult] = None
        self._fig = None
        self._canvas = None

    def build(self) -> Any:  # pragma: no cover - requires Qt/display
        from PyQt6.QtWidgets import (
            QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QFormLayout)
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        root = QWidget(); outer = QVBoxLayout(root)
        form = QFormLayout()
        self._moduli = QLineEdit("1.0, 0.5")
        self._times = QLineEdit("0.5, 3.0")
        form.addRow("Moduli g_i (comma):", self._moduli)
        form.addRow("Relax times τ_i (comma):", self._times)
        self._inputs = {"moduli": self._moduli, "times": self._times}
        run = QPushButton("Compile spectrum"); run.clicked.connect(self.on_run)
        self._status = QLabel("Ready.")
        self._result = self.ctrl.compute_from_modes([1.0, 0.5], [0.5, 3.0])
        self._fig = self.ctrl.make_figure(self._result)
        self._canvas = FigureCanvasQTAgg(self._fig)
        outer.addLayout(form); outer.addWidget(run); outer.addWidget(self._status)
        outer.addWidget(self._canvas, stretch=1)
        self._widget = root
        from metcore_gui.panel_features import wire_panel_features
        wire_panel_features(self, outer)
        return root

    def on_run(self) -> None:  # pragma: no cover - requires Qt
        try:
            g = [float(x) for x in self._moduli.text().split(",") if x.strip()]
            ts = [float(x) for x in self._times.text().split(",") if x.strip()]
            self._result = self.ctrl.compute_from_modes(g, ts)
            from metcore_gui.panel_features import refresh_canvas
            refresh_canvas(self)
            self._status.setText(f"{self._result.n_modes} modes · rms {self._result.rms_error:.2g}")
        except Exception as exc:
            self._status.setText(f"Error: {exc}")

    def export_basename(self) -> str:
        return "rheology_Gt"


def make_panel() -> RheologyPanel:
    return RheologyPanel()
