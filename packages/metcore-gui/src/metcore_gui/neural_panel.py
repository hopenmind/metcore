"""Neural domain panel: synaptic kernel → memory kernel → diagnosis."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional
import numpy as np
from metcore_gui.panel import ModulePanel


@dataclass
class NeuralResult:
    t: np.ndarray
    K: np.ndarray
    diagnosis: dict


class NeuralController:
    def compute(self, tau_rise=0.3, tau_decay=3.0, tau_max=20.0, n_points=256) -> NeuralResult:
        from memkern.adapters import neural_kernel
        from memkern import full_diagnosis
        t, K = neural_kernel(tau_rise, tau_decay, tau_max, n_points)
        diag = full_diagnosis(t, np.real(K), t_max=tau_max)
        return NeuralResult(t=t, K=K, diagnosis=diag)

    def make_figure(self, r: NeuralResult, branding: Any = None):
        from matplotlib.figure import Figure
        fig = Figure(figsize=(7.5, 4.6))
        self.draw_into(fig, r, branding)
        return fig

    def draw_into(self, fig, r: NeuralResult, branding: Any = None) -> None:
        """Redraw in place (keeps the canvas DPI; no figure swap)."""
        from metcore_export import apply_branding, BrandingConfig, theme_colors
        cfg = branding if branding is not None else BrandingConfig.load()
        th = theme_colors(cfg)
        fig.clear(); ax = fig.add_axes([0.12, 0.13, 0.80, 0.66])
        ax.plot(r.t, np.real(r.K), lw=1.8, color=th["primary"])
        ax.fill_between(r.t, np.real(r.K), color=th["fill"], alpha=0.08)
        ax.set_xlabel("time  t"); ax.set_ylabel("synaptic memory kernel  K(t)")
        ax.grid(True, alpha=0.25)
        emb = r.diagnosis.get("steps", {}).get("embeddability", {})
        ax.set_title(f"Neural retarded kernel - K={emb.get('K_est','?')} modes "
                     f"({emb.get('regime','?')})", fontsize=10, pad=8)
        apply_branding(fig, cfg)

    def series(self, r: NeuralResult):
        return [("t", r.t), ("K", np.real(r.K))]

    def export(self, fig, outdir, basename="neural_kernel", branding=None, formats=None):
        from metcore_export import export_all, BrandingConfig
        if getattr(fig, "canvas", None) is None or fig.canvas.__class__.__name__ == "FigureCanvasBase":
            from matplotlib.backends.backend_agg import FigureCanvasAgg; FigureCanvasAgg(fig)
        return export_all(fig, outdir, basename,
                          branding=branding or BrandingConfig.load(), formats=formats, apply=False)


class NeuralPanel(ModulePanel):
    display_name = "Synaptic K(t)"
    description = "Retarded synaptic/dendritic kernel → non-Markovian diagnosis."
    slug = "paper3a-neural"; domain = "Neural"

    def __init__(self) -> None:
        super().__init__(); self.ctrl = NeuralController()
        self._result = None; self._fig = None; self._canvas = None; self._w = {}

    def build(self) -> Any:  # pragma: no cover - Qt
        from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout,
            QDoubleSpinBox, QPushButton, QLabel)
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        root = QWidget(); outer = QVBoxLayout(root); form = QFormLayout()
        tr = QDoubleSpinBox(); tr.setRange(0.01, 100); tr.setValue(0.3); tr.setSingleStep(0.1)
        td = QDoubleSpinBox(); td.setRange(0.02, 100); td.setValue(3.0); td.setSingleStep(0.1)
        self._w = dict(tr=tr, td=td)
        self._inputs = self._w
        form.addRow("τ_rise:", tr); form.addRow("τ_decay:", td)
        run = QPushButton("Diagnose kernel"); run.clicked.connect(self.on_run)
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
            self._result = self.ctrl.compute(tau_rise=self._w["tr"].value(), tau_decay=self._w["td"].value())
            from metcore_gui.panel_features import refresh_canvas
            refresh_canvas(self)
            self._status.setText(self._result.diagnosis.get("summary", "")[:90])
        except Exception as exc:
            self._status.setText(f"Error: {exc}")

    def export_basename(self) -> str:
        return "neural_kernel"


def make_panel() -> NeuralPanel:
    return NeuralPanel()
