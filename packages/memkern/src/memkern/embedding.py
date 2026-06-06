"""
Exterior Lindbladian and the Lindblad-gap meter.

For the canonical pure-dephasing qubit driven by a memory kernel
C(τ) = Σ_k α_k e^{-β_k τ}, the exact coherence decay is governed by

    Γ(t) = ∫_0^t γ(t') dt' ,    γ(t') = ∫_0^{t'} Re C(τ) dτ ,

while the Markovian (Lindblad) approximation uses the *constant* asymptotic
rate  γ_M = γ(∞) = Re Σ_k α_k / β_k = Re Ĉ(0)  - exactly the exterior /
boundary Lindbladian of the ELT. This module makes the difference between the
two an explicit, plotted, integrated number: how wrong is Lindblad, here?

Everything is closed-form in the Prony modes (no ODE integration), so it is
exact up to the Prony fit itself.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
Author: DESVAUX G.J.Y. - Hope 'n Mind SASU - Research
"""

from __future__ import annotations

from typing import Any

import numpy as np


def exterior_lindblad_rate(alphas: np.ndarray, betas: np.ndarray) -> float:
    """Asymptotic dephasing rate γ_M = Re Σ α_k/β_k = Re Ĉ(0) (the ELT boundary)."""
    a = np.asarray(alphas, dtype=complex)
    b = np.asarray(betas, dtype=complex)
    return float(np.real(np.sum(a / b)))


def _Gamma(t: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Γ(t) = Re Σ α_k/β_k [ t - (1-e^{-β_k t})/β_k ]  (exact double integral)."""
    t = t[:, None]
    term = (a / b) * (t - (1.0 - np.exp(-b * t)) / b)
    return np.real(np.sum(term, axis=1))


def _gamma_rate(t: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Time-local rate γ(t) = Re Σ α_k (1-e^{-β_k t})/β_k."""
    t = t[:, None]
    return np.real(np.sum((a / b) * (1.0 - np.exp(-b * t)), axis=1))


def lindblad_gap(alphas: np.ndarray, betas: np.ndarray, *,
                 t_max: float = 20.0, n_points: int = 1024) -> dict[str, Any]:
    """Quantify the error of the Lindblad (exterior) approximation vs exact dephasing.

    Returns time series of the exact and Lindblad coherence |ρ_01(t)|, their gap,
    the asymptotic rate γ_M, the peak gap, and the time-integrated gap (an L1
    measure of 'how non-Markovian is this kernel, operationally').
    """
    a = np.asarray(alphas, dtype=complex)
    b = np.asarray(betas, dtype=complex)
    if np.any(np.real(b) <= 0):
        return {"error": "all Prony rates must have Re(β_k) > 0 (decaying modes)"}
    t = np.linspace(0.0, float(t_max), int(n_points))

    gamma_M = exterior_lindblad_rate(a, b)
    coh_exact = np.exp(-_Gamma(t, a, b))
    coh_lind = np.exp(-np.maximum(gamma_M, 0.0) * t)
    gap = np.abs(coh_exact - coh_lind)
    rate = _gamma_rate(t, a, b)

    return {
        "t": t.tolist(),
        "coherence_exact": coh_exact.tolist(),
        "coherence_lindblad": coh_lind.tolist(),
        "gap": gap.tolist(),
        "gamma_M": gamma_M,
        "peak_gap": float(gap.max()),
        "integrated_gap": float((np.trapezoid(gap, t) if hasattr(np, "trapezoid") else np.trapz(gap, t))),
        "rate_min": float(rate.min()),
        "verdict": ("Lindblad exact in the limit; transient gap only"
                    if rate.min() >= -1e-9 else
                    "Lindblad misses memory backflow (rate goes negative)"),
    }
