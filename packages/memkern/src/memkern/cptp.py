"""
CP-divisibility certifier (scalar / diagonal matrix-Bernstein).

For dephasing dynamics the time-local rate is γ(t) = Re Σ_k α_k (1-e^{-β_k t})/β_k.
Complete positivity of the divisor (CP-divisibility) holds iff γ(t) ≥ 0 for all
t ≥ 0 - the scalar case of the operator-valued matrix-Bernstein criterion
(Paper 1, Thm 3). This module certifies that, and when it fails, reports the
time windows where CP breaks (the memory-backflow intervals).

This is the *diagonal* certifier; the full operator-valued version requires the
system coupling operators and is the natural next extension.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
Author: DESVAUX G.J.Y. - Hope 'n Mind SASU - Research
"""

from __future__ import annotations

from typing import Any

import numpy as np


def cptp_certify(alphas: np.ndarray, betas: np.ndarray, *,
                 t_max: float = 20.0, n_points: int = 2048,
                 tol: float = 1e-9) -> dict[str, Any]:
    """Certify CP-divisibility of the dephasing channel built from Prony modes.

    Returns:
      cp_divisible : bool      - γ(t) ≥ -tol everywhere on the grid
      rate_min     : float     - most negative value of γ(t)
      breakdown    : list[[t0,t1]] - intervals where γ(t) < -tol (CP violated)
    """
    a = np.asarray(alphas, dtype=complex)
    b = np.asarray(betas, dtype=complex)
    if np.any(np.real(b) <= 0):
        return {"error": "all Prony rates must have Re(β_k) > 0"}
    t = np.linspace(0.0, float(t_max), int(n_points))
    rate = np.real(np.sum((a / b)[None, :] * (1.0 - np.exp(-b[None, :] * t[:, None])),
                          axis=1))
    neg = rate < -tol
    breakdown: list[list[float]] = []
    if neg.any():
        edges = np.diff(neg.astype(int))
        starts = list(np.where(edges == 1)[0] + 1)
        ends = list(np.where(edges == -1)[0] + 1)
        if neg[0]:
            starts = [0] + starts
        if neg[-1]:
            ends = ends + [len(t) - 1]
        breakdown = [[float(t[s]), float(t[e])] for s, e in zip(starts, ends)]
    return {
        "cp_divisible": bool(not neg.any()),
        "rate_min": float(rate.min()),
        "breakdown_intervals": breakdown,
        "verdict": ("CP-divisible: Lindblad form is admissible (matrix-Bernstein "
                    "satisfied in the diagonal sector)."
                    if not neg.any() else
                    "NOT CP-divisible: the kernel violates matrix-Bernstein; "
                    "memory backflow on the listed intervals."),
    }
