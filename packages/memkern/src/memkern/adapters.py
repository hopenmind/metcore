"""
Domain adapters - translate a domain's native input into a memory kernel C(τ).

One MET engine, several scientific dialects. Each adapter converts the language
of a field into the common C(τ) that the rest of the suite compiles, diagnoses
and embeds:

    quantum   : spectral density J(ω) + temperature  →  C(τ) = ∫ J(ω)[coth(βω/2)cos - i sin] dω
    neural    : synaptic rise/decay constants         →  bi-exponential kernel
    rheology  : relaxation modulus G(t)               →  (already Prony; see memkern-rheology)

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
Author: DESVAUX G.J.Y. - Hope 'n Mind SASU - Research
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.integrate import quad


# ─────────────────────────────── quantum ─────────────────────────────────────

def spectral_density(name: str, omega: np.ndarray, **p) -> np.ndarray:
    """Canonical bath spectral densities J(ω) (with built-in UV cutoff)."""
    w = np.asarray(omega, dtype=float)
    if name == "drude":
        lam = p.get("lam", 1.0); gamma = p.get("gamma", 1.0)
        return 2.0 * lam * gamma * w / (w**2 + gamma**2)
    if name == "ohmic":
        lam = p.get("lam", 1.0); wc = p.get("wc", 5.0)
        return lam * w * np.exp(-w / wc)
    if name == "subohmic":
        lam = p.get("lam", 1.0); s = p.get("s", 0.5); wc = p.get("wc", 5.0)
        return lam * wc**(1.0 - s) * np.power(np.maximum(w, 1e-12), s) * np.exp(-w / wc)
    if name in ("lorentzian", "underdamped"):
        lam = p.get("lam", 1.0); w0 = p.get("w0", 2.0); width = p.get("width", 0.3)
        return lam * width**2 / ((w - w0)**2 + width**2)
    raise KeyError(f"unknown spectral density {name!r}")


_WMAX = {"drude": lambda p: 80.0 * p.get("gamma", 1.0),
         "ohmic": lambda p: 40.0 * p.get("wc", 5.0),
         "subohmic": lambda p: 40.0 * p.get("wc", 5.0),
         "lorentzian": lambda p: p.get("w0", 2.0) + 60.0 * p.get("width", 0.3),
         "underdamped": lambda p: p.get("w0", 2.0) + 60.0 * p.get("width", 0.3)}


def quantum_kernel(spectral: str = "drude", T: float = 0.2,
                   tau_max: float = 15.0, n_points: int = 256,
                   **params) -> tuple[np.ndarray, np.ndarray]:
    """Bath correlation C(τ) for a spectral density at temperature T.

    C(τ) = ∫₀^∞ J(ω)[coth(βω/2) cos(ωτ) - i sin(ωτ)] dω   (Paper 1, Eq. C-spectral).
    """
    tau = np.linspace(0.0, float(tau_max), int(n_points))
    beta = 1.0 / max(float(T), 1e-6)
    wmax = _WMAX.get(spectral, lambda p: 50.0)(params)

    def J_coth(w: float) -> float:
        w = max(w, 1e-12)
        return float(spectral_density(spectral, w, **params) / np.tanh(beta * w / 2.0))

    def J_plain(w: float) -> float:
        return float(spectral_density(spectral, max(w, 1e-12), **params))

    C = np.empty(tau.size, dtype=complex)
    for i, t in enumerate(tau):
        re, _ = quad(J_coth, 0.0, wmax, weight="cos", wvar=t, limit=200)
        im, _ = quad(J_plain, 0.0, wmax, weight="sin", wvar=t, limit=200)
        C[i] = re - 1j * im
    return tau, C


# ─────────────────────────────── neural ──────────────────────────────────────

def neural_kernel(tau_rise: float = 0.3, tau_decay: float = 3.0,
                  tau_max: float = 20.0, n_points: int = 256
                  ) -> tuple[np.ndarray, np.ndarray]:
    """Synaptic/dendritic memory kernel - normalised difference of exponentials.

    K(t) ∝ e^{-t/τ_decay} - e^{-t/τ_rise}  (rise τ_rise < decay τ_decay). This is
    the retarded connectivity kernel of a neural population (Paper 3a); it is
    already a 2-mode Prony series, hence finitely embeddable by construction.
    """
    if tau_rise <= 0 or tau_decay <= 0:
        raise ValueError("time constants must be positive")
    if tau_rise >= tau_decay:
        tau_rise, tau_decay = min(tau_rise, tau_decay) * 0.5, max(tau_rise, tau_decay)
    t = np.linspace(0.0, float(tau_max), int(n_points))
    k = np.exp(-t / tau_decay) - np.exp(-t / tau_rise)
    peak = k.max() or 1.0
    return t, (k / peak).astype(complex)
