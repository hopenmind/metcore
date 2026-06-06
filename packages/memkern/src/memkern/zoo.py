"""
Kernel zoo - canonical memory kernels with analytic Prony modes and domain tags.

A reference/benchmark library: each entry returns a C(τ) sampler plus its exact
Prony decomposition (α_k, β_k) when one exists, and a domain label so the same
MET engine can be exercised across quantum, rheology, and neural inputs.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
Author: DESVAUX G.J.Y. - Hope 'n Mind SASU - Research
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

import numpy as np


@dataclass
class ZooKernel:
    name: str
    domain: str
    description: str
    C: Callable[[np.ndarray], np.ndarray]
    alphas: Optional[np.ndarray]   # None ⇒ no finite Prony (e.g. sub-ohmic)
    betas: Optional[np.ndarray]
    rational: bool


def drude(lam: float = 1.0, gamma: float = 1.0) -> ZooKernel:
    """Drude bath: C(τ)=λγ e^{-γτ}. Single real mode, CP-divisible. (quantum)"""
    a = np.array([lam * gamma], dtype=complex)
    b = np.array([gamma], dtype=complex)
    return ZooKernel("drude", "quantum", "Drude-Lorentz overdamped bath",
                     lambda t: lam * gamma * np.exp(-gamma * np.asarray(t)),
                     a, b, True)


def underdamped(lam: float = 1.0, w0: float = 2.0, gamma: float = 0.2) -> ZooKernel:
    """Underdamped/oscillating bath: complex-conjugate Prony pair → can break CP. (quantum)"""
    b = np.array([gamma + 1j * w0, gamma - 1j * w0], dtype=complex)
    a = np.array([0.5 * lam, 0.5 * lam], dtype=complex)
    def C(t):
        t = np.asarray(t)
        return lam * np.exp(-gamma * t) * np.cos(w0 * t)
    return ZooKernel("underdamped", "quantum",
                     "Underdamped (Brownian-oscillator) bath; oscillating kernel",
                     C, a, b, True)


def maxwell_wiechert(moduli=(1.0, 0.5), times=(0.5, 3.0)) -> ZooKernel:
    """Viscoelastic relaxation modulus G(t)=Σ g_i e^{-t/τ_i}. Prony is literal. (rheology)"""
    g = np.asarray(moduli, dtype=float)
    tau = np.asarray(times, dtype=float)
    a = g.astype(complex)
    b = (1.0 / tau).astype(complex)
    def G(t):
        t = np.asarray(t)[..., None]
        return (g * np.exp(-t / tau)).sum(axis=-1)
    return ZooKernel("maxwell_wiechert", "rheology",
                     "Maxwell-Wiechert relaxation modulus (Prony series, literal)",
                     G, a, b, True)


def subohmic(s: float = 0.5, wc: float = 1.0) -> ZooKernel:
    """Sub-ohmic power-law kernel: NO finite Prony (MET ε-extension only). (quantum)"""
    def C(t):
        t = np.asarray(t)
        return (1.0 + wc * t) ** (-(1.0 - s) - 1.0)
    return ZooKernel("subohmic", "quantum",
                     "Sub-ohmic power-law kernel; not rational (finite MET fails)",
                     C, None, None, False)


_ZOO = {k.__name__: k for k in (drude, underdamped, maxwell_wiechert, subohmic)}


def list_zoo() -> list[dict[str, Any]]:
    """List available canonical kernels with their domain and rationality."""
    out = []
    for name, fn in _ZOO.items():
        k = fn()
        out.append({"name": k.name, "domain": k.domain, "rational": k.rational,
                    "description": k.description})
    return out


def get_kernel(name: str, **params) -> ZooKernel:
    if name not in _ZOO:
        raise KeyError(f"unknown kernel {name!r}; choose from {sorted(_ZOO)}")
    return _ZOO[name](**params)
