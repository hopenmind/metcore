"""
Analytic shortcuts panel: one-stroke closed-form answers from the MET corpus.

Controller is Qt-free (headless-testable); the view is a thin Qt page with a
shortcut selector. Each shortcut replaces a numerical campaign by a formula;
the figure shows the relevant curve and the verdict carries the number.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
Author: DESVAUX G.J.Y. - Hope 'n Mind SASU - Research
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

from metcore_gui.panel import ModulePanel

SHORTCUTS = ("exterior_rate", "kuramoto_kc", "rf_resonance", "rt_scaling")

_LABELS = {
    "exterior_rate": "Exterior Lindbladian rate (gamma_M in one stroke)",
    "kuramoto_kc":   "Kuramoto threshold with memory K_c(M)",
    "rf_resonance":  "Resonance line shape of the threshold shift",
    "rt_scaling":    "Reaction-time scaling from kernel parameters",
}


def _parse_list(text) -> list[float]:
    if isinstance(text, (list, tuple)):
        return [float(x) for x in text]
    return [float(x) for x in str(text).split(",") if str(x).strip()]


@dataclass
class ShortcutResult:
    kind: str
    outputs: dict
    x: np.ndarray
    y: np.ndarray
    xlabel: str
    ylabel: str
    title: str
    meta: dict = field(default_factory=dict)


class ShortcutsController:
    """Pure-logic core: evaluates one closed-form shortcut + its curve."""

    def compute(self, kind: str = "exterior_rate", **p) -> ShortcutResult:
        import memkern.shortcuts as S
        if kind not in SHORTCUTS:
            raise ValueError(f"unknown shortcut {kind!r}; choose from {SHORTCUTS}")

        if kind == "exterior_rate":
            a = _parse_list(p.get("alphas", "1.0, 0.5"))
            b = _parse_list(p.get("betas", "0.5, 3.0"))
            out = S.exterior_rate(a, b)
            t = np.linspace(0.0, 5.0 / min(b), 600)
            k = np.real(sum(ai * np.exp(-bi * t) for ai, bi in zip(a, b)))
            return ShortcutResult(kind, out, t, k, "time  tau",
                                  "memory kernel  K(tau)",
                                  f"gamma_M = {out['gamma_markov']:.4g}   -   "
                                  f"{out['verdict']}")

        if kind == "kuramoto_kc":
            a = _parse_list(p.get("alphas", "1.0"))
            b = _parse_list(p.get("betas", "2.0"))
            gg = float(p.get("gamma_g", 0.5))
            out = S.kuramoto_kc(a, b, gamma_g=gg)
            t = np.linspace(0.0, 5.0 / min(b), 600)
            m = np.real(sum(ai * np.exp(-bi * t) for ai, bi in zip(a, b)))
            kc = out.get("K_c")
            ttl = (f"K_c(M) = {kc:.4g}  vs memoryless {out['K_c_memoryless']:.4g}"
                   if kc is not None else out["verdict"])
            return ShortcutResult(kind, out, t, m, "time  tau",
                                  "memory kernel  M(tau)", ttl)

        if kind == "rf_resonance":
            A = float(p.get("A", 0.1)); wp = float(p.get("omega_p", 2.0))
            w0 = float(p.get("omega0", 2.0)); g0 = float(p.get("gamma0", 0.3))
            m0 = float(p.get("m_base0", 1.0))
            out = S.rf_resonance_shift(A=A, omega_p=wp, omega0=w0,
                                       gamma0=g0, m_base0=m0)
            lo = max(1e-6, w0 - 6.0 * g0); hi = w0 + 6.0 * g0
            ws = np.linspace(lo, hi, 600)
            ys = []
            for w in ws:
                r = S.rf_resonance_shift(A=A, omega_p=float(w), omega0=w0,
                                         gamma0=g0, m_base0=m0)
                ys.append(r["shift_relative"] if r["shift_relative"]
                          is not None else np.nan)
            sh = out.get("shift_relative")
            ttl = (f"dKc/Kc({wp:g}) = {sh:+.4g}   -   {out['verdict']}"
                   if sh is not None else out["verdict"])
            return ShortcutResult(kind, out, ws, np.asarray(ys, float),
                                  "perturbation frequency  omega_p",
                                  "relative threshold shift", ttl,
                                  meta={"omega_p": wp})

        # rt_scaling
        tl = float(p.get("tau_l", 0.05)); td = float(p.get("tau_d", 0.02))
        th = float(p.get("theta", 1.0)); i0 = float(p.get("i0", 0.1))
        out = S.rt_scaling(tau_l=tl, tau_d=td, theta=th, i0=i0)
        xs = np.linspace(th * 1e-3, th * 0.999, 600)
        ys = tl + td * np.log(th / xs)
        return ShortcutResult(kind, out, xs, ys, "stimulus integral  I",
                              "predicted mean RT",
                              f"<RT>({i0:g}) = {out['rt_mean']:.4g}",
                              meta={"i0": i0})

    def make_figure(self, r: ShortcutResult, branding: Any = None):
        from matplotlib.figure import Figure
        fig = Figure(figsize=(7.5, 4.6))
        self.draw_into(fig, r, branding)
        return fig

    def draw_into(self, fig, r: ShortcutResult, branding: Any = None) -> None:
        from metcore_export import apply_branding, BrandingConfig, theme_colors
        cfg = branding if branding is not None else BrandingConfig.load()
        th = theme_colors(cfg)
        fig.clear()
        ax = fig.add_axes([0.12, 0.13, 0.80, 0.66])
        ax.plot(r.x, r.y, lw=1.8, color=th["primary"])
        ax.fill_between(r.x, r.y, color=th["fill"], alpha=0.08)
        marker = r.meta.get("omega_p", r.meta.get("i0"))
        if marker is not None:
            ax.axvline(float(marker), color=th["secondary"], lw=1.2, ls="--")
        ax.set_xlabel(r.xlabel); ax.set_ylabel(r.ylabel)
        ax.grid(True, alpha=0.25)
        ax.set_title(r.title, fontsize=10, pad=8)
        apply_branding(fig, cfg)

    def series(self, r: ShortcutResult):
        return [(r.xlabel, r.x), (r.ylabel, r.y)]

    def export(self, fig, outdir, basename="shortcut", branding=None,
               formats=None):
        from metcore_export import export_all, BrandingConfig
        if getattr(fig, "canvas", None) is None or \
                fig.canvas.__class__.__name__ == "FigureCanvasBase":
            from matplotlib.backends.backend_agg import FigureCanvasAgg
            FigureCanvasAgg(fig)
        return export_all(fig, outdir, basename,
                          branding=branding or BrandingConfig.load(),
                          formats=formats, apply=False)


# ─────────────────────────────────── view ────────────────────────────────────

class ShortcutsPanel(ModulePanel):
    display_name = "Analytic shortcuts"
    description = "Closed-form answers in one stroke where the normal route is hours of simulation."
    slug = "met-shortcuts"
    domain = "Shortcuts"

    def __init__(self) -> None:
        super().__init__()
        self.ctrl = ShortcutsController()
        self._result: Optional[ShortcutResult] = None
        self._fig = None
        self._canvas = None
        self._inputs: dict[str, Any] = {}

    def build(self) -> Any:  # pragma: no cover - Qt/display
        from PyQt6.QtWidgets import (
            QWidget, QVBoxLayout, QFormLayout, QComboBox, QLineEdit,
            QDoubleSpinBox, QPushButton, QLabel, QStackedWidget)
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

        root = QWidget(); outer = QVBoxLayout(root)
        sel = QComboBox()
        for k in SHORTCUTS:
            sel.addItem(_LABELS[k], k)
        outer.addWidget(sel)

        def dsb(v, lo=0.000001, hi=1000.0, step=0.05):
            w = QDoubleSpinBox(); w.setDecimals(4)
            w.setRange(lo, hi); w.setValue(v); w.setSingleStep(step)
            return w

        stack = QStackedWidget()
        pages: dict[str, dict[str, Any]] = {}

        # exterior_rate page
        w1 = QWidget(); f1 = QFormLayout(w1)
        e_a = QLineEdit("1.0, 0.5"); e_b = QLineEdit("0.5, 3.0")
        f1.addRow("Prony amplitudes alpha_k:", e_a)
        f1.addRow("Prony rates beta_k:", e_b)
        pages["exterior_rate"] = {"alphas": e_a, "betas": e_b}
        stack.addWidget(w1)

        # kuramoto page
        w2 = QWidget(); f2 = QFormLayout(w2)
        k_a = QLineEdit("1.0"); k_b = QLineEdit("2.0")
        k_g = dsb(0.5)
        f2.addRow("Kernel amplitudes alpha_k:", k_a)
        f2.addRow("Kernel rates beta_k:", k_b)
        f2.addRow("Frequency spread gamma_g:", k_g)
        pages["kuramoto_kc"] = {"alphas": k_a, "betas": k_b, "gamma_g": k_g}
        stack.addWidget(w2)

        # rf resonance page
        w3 = QWidget(); f3 = QFormLayout(w3)
        r_A = dsb(0.1); r_wp = dsb(2.0); r_w0 = dsb(2.0)
        r_g0 = dsb(0.3); r_m0 = dsb(1.0)
        f3.addRow("Perturbation amplitude A:", r_A)
        f3.addRow("Perturbation frequency omega_p:", r_wp)
        f3.addRow("Kernel pole omega_0:", r_w0)
        f3.addRow("Kernel damping gamma_0:", r_g0)
        f3.addRow("Base M_hat(0):", r_m0)
        pages["rf_resonance"] = {"A": r_A, "omega_p": r_wp, "omega0": r_w0,
                                 "gamma0": r_g0, "m_base0": r_m0}
        stack.addWidget(w3)

        # rt scaling page
        w4 = QWidget(); f4 = QFormLayout(w4)
        t_l = dsb(0.05); t_d = dsb(0.02); t_th = dsb(1.0); t_i = dsb(0.1)
        f4.addRow("Conduction lag tau_l:", t_l)
        f4.addRow("Dendritic constant tau_d:", t_d)
        f4.addRow("Decision threshold theta:", t_th)
        f4.addRow("Stimulus integral I_0:", t_i)
        pages["rt_scaling"] = {"tau_l": t_l, "tau_d": t_d,
                               "theta": t_th, "i0": t_i}
        stack.addWidget(w4)

        sel.currentIndexChanged.connect(stack.setCurrentIndex)
        outer.addWidget(stack)
        self._sel = sel
        self._pages = pages

        # live update watches every input of every page + the selector
        self._inputs = {"shortcut": sel}
        for kind, ws in pages.items():
            for name, w in ws.items():
                self._inputs[f"{kind}.{name}"] = w

        run = QPushButton("Evaluate (one stroke)")
        run.clicked.connect(self.on_run)
        outer.addWidget(run)
        self._status = QLabel("Pick a shortcut and evaluate: the answer is "
                              "a formula, not a simulation.")
        outer.addWidget(self._status)

        self._result = self.ctrl.compute()
        self._fig = self.ctrl.make_figure(self._result)
        self._canvas = FigureCanvasQTAgg(self._fig)
        outer.addWidget(self._canvas, stretch=1)
        self._widget = root
        from metcore_gui.panel_features import wire_panel_features
        wire_panel_features(self, outer)
        return root

    def _read_params(self) -> dict:
        kind = self._sel.currentData()
        params: dict[str, Any] = {"kind": kind}
        for name, w in self._pages[kind].items():
            params[name] = w.text() if hasattr(w, "text") and not \
                hasattr(w, "value") else w.value()
        return params

    def on_run(self) -> None:  # pragma: no cover - Qt
        try:
            self._result = self.ctrl.compute(**self._read_params())
            from metcore_gui.panel_features import refresh_canvas
            refresh_canvas(self)
            self._status.setText(str(self._result.outputs.get("verdict", "")))
        except Exception as exc:
            self._status.setText(f"Error: {exc}")

    def export_basename(self) -> str:
        r = getattr(self, "_result", None)
        return f"shortcut_{r.kind}" if r is not None else "shortcut"


def make_panel() -> ShortcutsPanel:
    return ShortcutsPanel()
