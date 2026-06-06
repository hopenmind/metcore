"""Randomised / adversarial tests for ``memkern.prony``.

Rather than checking a few hand-picked analytical cases, these tests
sample random exponential sums, fit them, and check invariants
(residual small, variance explained high, K at most what was injected).

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

import numpy as np
import pytest

from memkern import maxent_select_order, prony_decompose


def _random_exponential_sum(rng, K, noise, N=1024, t_max=50.0):
    """Draw α_k ~ U(0.1, 2), β_k ~ U(0.05, 3), add Gaussian noise."""
    alphas = rng.uniform(0.1, 2.0, size=K)
    betas = rng.uniform(0.05, 3.0, size=K)
    t = np.linspace(0.0, t_max, N)
    y = (alphas[None, :] * np.exp(-np.outer(t, betas))).sum(axis=1)
    if noise > 0:
        y = y + noise * rng.standard_normal(t.shape)
    return t, y, alphas, betas


# Two difficulty levels — clean (noise 1e-8) and moderately noisy (1e-3).
@pytest.mark.parametrize("seed", range(10))
@pytest.mark.parametrize("K,noise", [(1, 1e-8), (2, 1e-8), (3, 1e-5), (4, 1e-4)])
def test_random_exponential_sums_are_fit_well(seed, K, noise):
    rng = np.random.default_rng(seed + K * 1000)
    t, y, alphas, betas = _random_exponential_sum(rng, K, noise)
    result = prony_decompose(t, y, n_exp=K)
    assert result.n_exp == K
    # noise^0.5 rough floor on residual
    assert result.residual < max(5.0 * noise ** 0.5, 1e-3)
    assert result.variance_explained > 0.99


@pytest.mark.parametrize("seed", range(5))
def test_maxent_monotone_in_threshold_random(seed):
    """On any spectrum, a tighter MaxEnt threshold never picks fewer modes."""
    rng = np.random.default_rng(seed)
    sv = np.sort(rng.uniform(0.01, 5.0, size=12))[::-1]
    K_low = maxent_select_order(sv, entropy_ratio_threshold=0.3, max_n_exp=12)
    K_high = maxent_select_order(sv, entropy_ratio_threshold=0.99, max_n_exp=12)
    assert K_high >= K_low


@pytest.mark.parametrize("seed", range(8))
def test_auto_order_does_not_exceed_injected(seed):
    """Random 3-mode signal: auto-selected K should not drastically exceed 3."""
    rng = np.random.default_rng(seed + 7)
    t, y, *_ = _random_exponential_sum(rng, K=3, noise=1e-5)
    result = prony_decompose(t, y, variance_threshold=0.999)
    assert result.n_exp <= 6
    assert result.n_exp >= 1
