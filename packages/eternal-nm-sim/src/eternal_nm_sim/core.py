"""Core of eternal-nm-sim.

The Pauli-channel master equation

    dρ/dt = Σ_{i∈{x,y,z}} γ_i(t) [ σ_i ρ σ_i - ρ ]

produces, on the Bloch sphere, the diagonal affine map

    λ_x(t) = exp(- ∫₀^t [γ_y(s) + γ_z(s)] ds)
    λ_y(t) = exp(- ∫₀^t [γ_z(s) + γ_x(s)] ds)
    λ_z(t) = exp(- ∫₀^t [γ_x(s) + γ_y(s)] ds)

so that M(t) = diag(λ_x, λ_y, λ_z). CPTP holds when
γ_x + γ_y + γ_z ≥ 0 at all times. CP-divisibility additionally
requires each individual γ_i ≥ 0.

The Hall 2014 canonical eternal-NM choice is

    γ_x = γ_y = 1 ,        γ_z(t) = -tanh(t)

giving CPTP (sum = 2 - tanh(t) ≥ 1) while γ_z < 0 everywhere, so the
channel is not CP-divisible. Remarkably, for this choice the BLP
measure is 0 (no pair-wise trace-distance revival ever occurs) —
Hall's point being that information-backflow is a strictly weaker
witness than CP-divisibility.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

from typing import Callable

import numpy as np
from obliquity_ng import ng_from_bloch_matrices


# ──────────────────────────────────────────────────────────────────────────────
#  Pauli-channel construction
# ──────────────────────────────────────────────────────────────────────────────

def pauli_channel(gamma_x: Callable[[np.ndarray], np.ndarray],
                  gamma_y: Callable[[np.ndarray], np.ndarray],
                  gamma_z: Callable[[np.ndarray], np.ndarray]
                  ) -> Callable[[np.ndarray], np.ndarray]:
    """Build a ``t -> M(t)`` Pauli channel from γ_x, γ_y, γ_z rate
    functions (each accepts an ndarray of times and returns an ndarray).
    """
    def _integrate(fn, t):
        vals = np.asarray(fn(t), dtype=float)
        # cumulative trapezoidal starting at 0
        cum = np.concatenate(([0.0], np.cumsum(0.5 * (vals[1:] + vals[:-1]) * np.diff(t))))
        return cum

    def M(t):
        t = np.asarray(t, dtype=float)
        Ix = _integrate(gamma_x, t)
        Iy = _integrate(gamma_y, t)
        Iz = _integrate(gamma_z, t)
        lam_x = np.exp(-(Iy + Iz))
        lam_y = np.exp(-(Iz + Ix))
        lam_z = np.exp(-(Ix + Iy))
        out = np.zeros(t.shape + (3, 3))
        out[..., 0, 0] = lam_x
        out[..., 1, 1] = lam_y
        out[..., 2, 2] = lam_z
        return out
    return M


def hall_channel() -> Callable[[np.ndarray], np.ndarray]:
    """Canonical Hall 2014 eternal-NM Pauli channel.

    γ_x = γ_y = 1, γ_z(t) = -tanh(t). The Bloch factors reduce to

        λ_x(t) = λ_y(t) = (1 + e^{-2t}) / 2
        λ_z(t) = e^{-2t}

    so |det M(t)| = (λ_x)² · λ_z is monotone-decreasing — the hallmark
    of an eternally non-Markovian channel that leaves no volume-level
    fingerprint (and likewise no BLP signal).
    """
    return pauli_channel(
        gamma_x=lambda t: np.ones_like(np.asarray(t, dtype=float)),
        gamma_y=lambda t: np.ones_like(np.asarray(t, dtype=float)),
        gamma_z=lambda t: -np.tanh(np.asarray(t, dtype=float)),
    )


# ──────────────────────────────────────────────────────────────────────────────
#  BLP measure
# ──────────────────────────────────────────────────────────────────────────────

def _trace_distance_pair(M_t: np.ndarray, r1: np.ndarray, r2: np.ndarray
                         ) -> np.ndarray:
    """Trace distance ‖ρ_1(t) − ρ_2(t)‖_1/2 for a Pauli-diagonal channel.

    For a qubit, ‖ρ_a − ρ_b‖_1 / 2 = ‖r_a − r_b‖_2 / 2 where r_{a,b}
    are the Bloch vectors. Under an affine channel M, the difference
    of vectors evolves as ``M(t) · (r_a − r_b)`` so the channel-affine
    part drops out of the distance.
    """
    diff0 = np.asarray(r1, dtype=float) - np.asarray(r2, dtype=float)
    # For Pauli-diagonal M: M(t) @ diff0 is the evolved Bloch difference.
    evolved = np.einsum("tij,j->ti", M_t, diff0)
    return 0.5 * np.linalg.norm(evolved, axis=1)


def blp_measure(M: np.ndarray, t: np.ndarray, *,
                n_samples: int = 30, seed: int | None = 0) -> float:
    """Approximate the BLP non-Markovianity measure.

    The BLP measure is

        N_BLP = sup_{ρ_1, ρ_2} ∫_{dD/dt > 0} dD/dt dt ,

    where D is the trace distance. We approximate the supremum by
    sampling ``n_samples`` antipodal pairs of pure states on the Bloch
    sphere (the optimum always lies on two pure antipodal states for
    unital qubit channels) and taking the maximum over the sample.

    For Pauli-diagonal channels the optimal pair aligns with whichever
    axis has the largest revival — sampling covers that robustly.
    """
    M = np.asarray(M, dtype=float)
    t = np.asarray(t, dtype=float)
    if M.ndim != 3 or M.shape[1:] != (3, 3):
        raise ValueError(f"M must have shape (T, 3, 3); got {M.shape}")
    if t.size != M.shape[0]:
        raise ValueError("t length must match M[0]")

    rng = np.random.default_rng(seed)
    # Unit Bloch-sphere directions; antipodal pair = +r / -r.
    directions = rng.standard_normal((n_samples, 3))
    directions = directions / np.linalg.norm(directions, axis=1, keepdims=True)

    best = 0.0
    for k in range(n_samples):
        r1 = directions[k]
        r2 = -directions[k]
        d = _trace_distance_pair(M, r1, r2)
        dd = np.gradient(d, t)
        positive = np.where(dd > 0, dd, 0.0)
        val = float(np.trapezoid(positive, t))
        if val > best:
            best = val
    return best


# ──────────────────────────────────────────────────────────────────────────────
#  Side-by-side diagnostic
# ──────────────────────────────────────────────────────────────────────────────

def compare_blp_ng(channels: dict[str, Callable[[np.ndarray], np.ndarray]],
                   t: np.ndarray, *,
                   n_blp_samples: int = 30,
                   seed: int | None = 0) -> dict[str, dict[str, float]]:
    """Compute BLP and N_G for every named channel.

    Returns a dict ``{name: {"BLP": ..., "N_G": ...}}``.
    """
    out: dict[str, dict[str, float]] = {}
    for name, builder in channels.items():
        M = builder(t)
        out[name] = {
            "BLP": blp_measure(M, t, n_samples=n_blp_samples, seed=seed),
            "N_G": ng_from_bloch_matrices(M, t),
        }
    return out
