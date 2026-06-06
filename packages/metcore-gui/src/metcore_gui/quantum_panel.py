"""Quantum domain panel: spectral density J(ω) → C(τ) → full diagnosis."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional
import numpy as np
from metcore_gui.panel import ModulePanel

SPECTRA = ("drude", "ohmic", "subohmic", "lorentzian")


@dataclass
class QuantumResult:
    tau: np.ndarray
    C: np.ndarray
    diagnosis: dict


class QuantumController:
    def compute(self, spectral="drude", T=0.2, lam=1.0, gamma=1.0, wc=5.0,
                s=0.5, tau_max=15.0, n_points=200) -> QuantumResult:
        from memkern.adapters import quantum_kernel
        from memkern import full_diagnosis
        params = {"lam": lam, "gamma": gamma, "wc": wc, "s": s}
        tau, C = quantum_kernel(spectral, T=T, tau_max=tau_max, n_points=n_points, **params)
        diag = full_diagnosis(tau, np.real(C), t_max=tau_max)
        return QuantumResult(tau=tau, C=C, diagnosis=diag)

    def make_figure(self, r: QuantumResult, branding: Any = None):
        from matplotlib.figure import Figure
        fig = Figure(figsize=(7.5, 4.6))
        self.draw_into(fig, r, branding)
        return fig

    def draw_into(self, fig, r: QuantumResult, branding: Any = None) -> None:
        """Redraw in place (keeps the canvas DPI; no figure swap)."""
        from metcore_export import apply_branding, BrandingConfig, theme_colors
        cfg = branding if branding is not None else BrandingConfig.load()
        th = theme_colors(cfg)
        fig.clear(); ax = fig.add_axes([0.12, 0.13, 0.80, 0.66])
        ax.plot(r.tau, np.real(r.C), lw=1.7, color=th["primary"], label="Re C(τ)")
        ax.plot(r.tau, np.imag(r.C), lw=1.2, color=th["secondary"], ls="--", label="Im C(τ)")
        ax.set_xlabel("time  τ"); ax.set_ylabel("bath correlation  C(τ)")
        ax.legend(fontsize=8); ax.grid(True, alpha=0.25)
        emb = r.diagnosis.get("steps", {}).get("embeddability", {})
        ax.set_title(f"Quantum bath - {emb.get('regime','?')}, K={emb.get('K_est','?')}",
                     fontsize=10, pad=8)
        apply_branding(fig, cfg)

    def series(self, r: QuantumResult):
        return [("tau", r.tau), ("Re_C", np.real(r.C)), ("Im_C", np.imag(r.C))]

    def export(self, fig, outdir, basename="quantum_kernel", branding=None, formats=None):
        from metcore_export import export_all, BrandingConfig
        if getattr(fig, "canvas", None) is None or fig.canvas.__class__.__name__ == "FigureCanvasBase":
            from matplotlib.backends.backend_agg import FigureCanvasAgg; FigureCanvasAgg(fig)
        return export_all(fig, outdir, basename,
                          branding=branding or BrandingConfig.load(), formats=formats, apply=False)


class QuantumPanel(ModulePanel):
    display_name = "Bath J(ω)"
    description = "Spectral density → bath correlation → non-Markovian diagnosis."
    slug = "boltz-kernel"; domain = "Quantum"

    def __init__(self) -> None:
        super().__init__(); self.ctrl = QuantumController()
        self._result = None; self._fig = None; self._canvas = None; self._w = {}

    def build(self) -> Any:  # pragma: no cover - Qt
        from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QComboBox,
            QDoubleSpinBox, QSpinBox, QPushButton, QLabel)
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        root = QWidget(); outer = QVBoxLayout(root); form = QFormLayout()
        sp = QComboBox(); sp.addItems(SPECTRA)
        T = QDoubleSpinBox(); T.setRange(0.001, 100); T.setValue(0.2); T.setSingleStep(0.05)
        lam = QDoubleSpinBox(); lam.setRange(0.001, 100); lam.setValue(1.0)
        gamma = QDoubleSpinBox(); gamma.setRange(0.001, 100); gamma.setValue(1.0)
        wc = QDoubleSpinBox(); wc.setRange(0.1, 100); wc.setValue(5.0)
        self._w = dict(spectral=sp, T=T, lam=lam, gamma=gamma, wc=wc)
        self._inputs = self._w
        for lab, wid in (("Spectral density", sp), ("Temperature T", T), ("λ", lam),
                         ("γ (Drude)", gamma), ("ω_c (Ohmic)", wc)):
            form.addRow(lab + ":", wid)
        run = QPushButton("Diagnose bath"); run.clicked.connect(self.on_run)
        self._status = QLabel("Ready.")
        self._result = self.ctrl.compute(); self._fig = self.ctrl.make_figure(self._result)
        self._canvas = FigureCanvasQTAgg(self._fig)
        outer.addLayout(form); outer.addWidget(run); outer.addWidget(self._status)
        outer.addWidget(self._canvas, stretch=1); self._widget = root
        from metcore_gui.panel_features import wire_panel_features
        wire_panel_features(self, outer)
        return root

    def on_run(self) -> None:  # pragma: no cover - Qt
        try:
            w = self._w
            self._result = self.ctrl.compute(spectral=w["spectral"].currentText(),
                T=w["T"].value(), lam=w["lam"].value(), gamma=w["gamma"].value(), wc=w["wc"].value())
            from metcore_gui.panel_features import refresh_canvas
            refresh_canvas(self)
            self._status.setText(self._result.diagnosis.get("summary", "")[:90])
        except Exception as exc:
            self._status.setText(f"Error: {exc}")

    def export_basename(self) -> str:
        return "quantum_bath"


def make_panel() -> QuantumPanel:
    return QuantumPanel()
