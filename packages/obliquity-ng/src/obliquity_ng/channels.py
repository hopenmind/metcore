"""Canonical qubit channels for N_G testing and demos.

Each channel returns a function ``t -> M(t)`` where ``M(t)`` is the 3×3
real affine-contraction map on the Bloch vector. Sign conventions match
Nielsen-Chuang, chap. 8.

The channels here are CP-divisible (Markovian) unless their name says
otherwise, so they serve as negative controls for N_G: the measure
should evaluate to zero on them up to numerical floor.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

from typing import Callable

import numpy as np


def dephasing_channel(gamma: float) -> Callable[[np.ndarray], np.ndarray]:
    """Pure dephasing: diagonal M(t) = diag(e^{-γt}, e^{-γt}, 1).

    CP-divisible for γ ≥ 0. Expected N_G = 0.
    """
    def M(t):
        t = np.asarray(t, dtype=float)
        e = np.exp(-gamma * t)
        out = np.zeros(t.shape + (3, 3))
        out[..., 0, 0] = e
        out[..., 1, 1] = e
        out[..., 2, 2] = 1.0
        return out
    return M


def depolarizing_channel(gamma: float) -> Callable[[np.ndarray], np.ndarray]:
    """Depolarizing: isotropic shrinking M(t) = e^{-γt} · I.

    CP-divisible for γ ≥ 0. Expected N_G = 0.
    """
    def M(t):
        t = np.asarray(t, dtype=float)
        e = np.exp(-gamma * t)
        out = np.zeros(t.shape + (3, 3))
        out[..., 0, 0] = e
        out[..., 1, 1] = e
        out[..., 2, 2] = e
        return out
    return M


def amplitude_damping_channel(gamma: float) -> Callable[[np.ndarray], np.ndarray]:
    """Markovian amplitude damping at rate γ.

    On the Bloch sphere: M(t) = diag(e^{-γt/2}, e^{-γt/2}, e^{-γt}).
    (The affine part c(t) is non-zero but does not enter |det M|.)
    CP-divisible → Expected N_G = 0.
    """
    def M(t):
        t = np.asarray(t, dtype=float)
        e_xy = np.exp(-gamma * t / 2.0)
        e_z = np.exp(-gamma * t)
        out = np.zeros(t.shape + (3, 3))
        out[..., 0, 0] = e_xy
        out[..., 1, 1] = e_xy
        out[..., 2, 2] = e_z
        return out
    return M


def nonmarkovian_revival_channel(gamma: float, omega: float
                                 ) -> Callable[[np.ndarray], np.ndarray]:
    """Toy non-Markovian channel with Rabi-like revivals.

    M(t) = diag(f(t), f(t), g(t)) with

        f(t) = exp(-γ t) · cos(ω t)²
        g(t) = exp(-γ t)

    ``|det M(t)| = f(t)² · g(t)`` oscillates and recovers periodically;
    its derivative is positive on intervals where the envelope grows,
    giving N_G > 0. This is the canonical toy fixture exercising
    non-zero N_G without requiring a full spin-boson solver.
    """
    def M(t):
        t = np.asarray(t, dtype=float)
        env = np.exp(-gamma * t)
        c2 = np.cos(omega * t) ** 2
        out = np.zeros(t.shape + (3, 3))
        out[..., 0, 0] = env * c2
        out[..., 1, 1] = env * c2
        out[..., 2, 2] = env
        return out
    return M
