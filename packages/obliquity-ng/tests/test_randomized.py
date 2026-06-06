"""Randomised tests for ng-vol — random contraction channels must have
N_G = 0, random non-monotone channels must have N_G > 0 and finite.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

import numpy as np
import pytest

from obliquity_ng import ng_from_bloch_matrices


def _random_monotone_contraction(rng, t):
    """Random diagonal Bloch map M(t) with each component monotone-decreasing.

    For each axis, pick a decay rate γ ~ U(0.1, 2). Equivalent to a
    unital Markovian channel in that axis — should give N_G = 0.
    """
    rates = rng.uniform(0.1, 2.0, size=3)
    out = np.zeros(t.shape + (3, 3))
    for i in range(3):
        out[..., i, i] = np.exp(-rates[i] * t)
    return out


def _random_oscillating_channel(rng, t):
    """Diagonal Bloch map with one axis carrying a random-frequency
    multiplicative oscillation. Guaranteed non-monotone |det M| ⇒ N_G > 0.
    """
    gamma = rng.uniform(0.05, 0.3)
    omega = rng.uniform(1.0, 4.0)
    rates = rng.uniform(0.1, 1.0, size=3)
    axis = int(rng.integers(0, 3))
    out = np.zeros(t.shape + (3, 3))
    for i in range(3):
        if i == axis:
            out[..., i, i] = np.exp(-gamma * t) * np.cos(omega * t) ** 2
        else:
            out[..., i, i] = np.exp(-rates[i] * t)
    return out


@pytest.mark.parametrize("seed", range(20))
def test_random_monotone_contraction_is_markovian(seed):
    rng = np.random.default_rng(seed)
    t = np.linspace(0.0, 10.0, 1024)
    M = _random_monotone_contraction(rng, t)
    ng = ng_from_bloch_matrices(M, t)
    assert 0.0 <= ng < 1e-6


@pytest.mark.parametrize("seed", range(20))
def test_random_oscillating_channel_is_nonmarkovian(seed):
    rng = np.random.default_rng(seed + 1000)
    t = np.linspace(0.0, 10.0, 2048)
    M = _random_oscillating_channel(rng, t)
    ng = ng_from_bloch_matrices(M, t)
    assert ng > 1e-3
    assert np.isfinite(ng)


@pytest.mark.parametrize("seed", range(10))
def test_ng_is_always_nonnegative(seed):
    """Whatever random channel we throw at it, N_G is non-negative and finite."""
    rng = np.random.default_rng(seed + 500)
    t = np.linspace(0.0, 8.0, 1024)
    # Mix: some monotone, some oscillating — chosen per seed
    M = (_random_monotone_contraction(rng, t)
         if seed % 2 == 0
         else _random_oscillating_channel(rng, t))
    ng = ng_from_bloch_matrices(M, t)
    assert ng >= 0.0
    assert np.isfinite(ng)
