"""Randomised tests for memkern-rheology — random Maxwell-Wiechert
parameters, verify recovery and forward-model roundtrip.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

import numpy as np
import pytest

from memkern_rheology import evaluate_modulus, fit_maxwell_wiechert


def _draw_params(rng, K):
    """Random G_inf, G_k, τ_k with well-spread τ (no near-degeneracies)."""
    G_inf = rng.uniform(0.05, 1.0)
    G_k = rng.uniform(0.2, 2.0, size=K)
    # draw decades for τ to avoid two modes collapsing into one
    decades = rng.uniform(-1.0, 1.5, size=K)
    decades = np.sort(decades)
    # enforce minimum half-decade separation
    for i in range(1, K):
        if decades[i] - decades[i - 1] < 0.5:
            decades[i] = decades[i - 1] + 0.5
    tau_k = 10.0 ** decades
    return G_inf, G_k, tau_k


@pytest.mark.parametrize("seed", range(8))
@pytest.mark.parametrize("K", [1, 2, 3])
def test_fit_recovers_random_modes(seed, K):
    """Fix K manually so this test isolates the fitter from the order
    selector (which is exercised in its own tests). Generous τ tolerance
    because 3-mode random draws can place τ awkwardly close."""
    rng = np.random.default_rng(seed * 17 + K)
    G_inf, G_k, tau_k = _draw_params(rng, K)
    # Cover at least 20× the slowest τ for stable fit of the tail
    t_max = 20.0 * tau_k.max()
    t = np.linspace(0.0, t_max, 2048)
    G = evaluate_modulus(t, G_inf, G_k, tau_k) + 1e-6 * rng.standard_normal(t.shape)

    res = fit_maxwell_wiechert(t, G, n_modes=K, method="manual")

    assert res.n_modes == K
    assert res.residual < 0.05

    # Every injected τ should have a recovered τ within 50 % — tolerance
    # loose on purpose, randomised draws routinely land two modes near
    # each other and the fit splits differently than the truth labelling.
    for t_true in tau_k:
        best_err = min(abs(t_fit - t_true) / t_true for t_fit in res.tau_k)
        assert best_err < 0.5, f"τ={t_true:.3g} not recovered (best err {best_err:.2%})"


@pytest.mark.parametrize("seed", range(5))
def test_forward_roundtrip_random(seed):
    """Forward model: fit then predict should match the input within noise."""
    rng = np.random.default_rng(seed + 100)
    G_inf, G_k, tau_k = _draw_params(rng, K=2)
    t = np.linspace(0.0, 10.0 * tau_k.max(), 1024)
    G = evaluate_modulus(t, G_inf, G_k, tau_k)

    res = fit_maxwell_wiechert(t, G, method="maxent", max_n_modes=5)
    G_pred = evaluate_modulus(t, res.G_inf, res.G_k, res.tau_k)
    rmse = float(np.sqrt(((G_pred - G) ** 2).mean()))
    assert rmse < 0.01
