"""Tests for memkern-rheology.

Analytical reference cases with known Maxwell-Wiechert parameters.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

import numpy as np
import pytest

from memkern_rheology import (
    MaxwellWiechertResult,
    evaluate_modulus,
    fit_maxwell_wiechert,
    storage_loss_moduli,
)


def _synth(t, G_inf, Gs, taus, noise=0.0):
    y = np.full_like(t, G_inf, dtype=float)
    for g, tau in zip(Gs, taus):
        y = y + g * np.exp(-t / tau)
    if noise > 0:
        y = y + noise * np.random.default_rng(0).standard_normal(t.shape)
    return y


# ──────────────────────────────────────────────────────────────────────────────
#  evaluate_modulus / storage_loss_moduli
# ──────────────────────────────────────────────────────────────────────────────

def test_evaluate_shape_and_offset():
    t = np.linspace(0, 10, 64)
    y = evaluate_modulus(t, G_inf=2.0, G_k=np.array([]), tau_k=np.array([]))
    assert y.shape == t.shape
    assert np.allclose(y, 2.0)


def test_evaluate_single_mode_matches_formula():
    t = np.linspace(0, 5, 128)
    G_inf, G, tau = 0.1, 1.2, 0.7
    y = evaluate_modulus(t, G_inf, np.array([G]), np.array([tau]))
    assert np.allclose(y, G_inf + G * np.exp(-t / tau), atol=1e-12)


def test_storage_loss_limits():
    """Pure plateau: G' = G_inf + G_k at high ω, G'' → 0 at high ω."""
    omega = np.array([1e-6, 1e6])
    G_storage, G_loss = storage_loss_moduli(
        omega, G_inf=0.2, G_k=np.array([1.0, 0.5]),
        tau_k=np.array([10.0, 0.1]),
    )
    # Low-ω limit: G' → G_inf
    assert np.isclose(G_storage[0], 0.2, atol=1e-8)
    # High-ω limit: G' → G_inf + sum(G_k)
    assert np.isclose(G_storage[1], 0.2 + 1.0 + 0.5, rtol=1e-6)
    # G'' bounded and small at extremes
    assert G_loss[0] < 1e-4
    assert G_loss[1] < 1e-4


# ──────────────────────────────────────────────────────────────────────────────
#  fit_maxwell_wiechert
# ──────────────────────────────────────────────────────────────────────────────

def test_fit_rejects_short_input():
    t = np.linspace(0, 1, 3)
    with pytest.raises(ValueError, match="at least 4"):
        fit_maxwell_wiechert(t, t)


def test_fit_rejects_shape_mismatch():
    t = np.linspace(0, 1, 20)
    with pytest.raises(ValueError, match="equal length"):
        fit_maxwell_wiechert(t, t[:10])


def test_fit_rejects_manual_without_n_modes():
    t = np.linspace(0, 1, 20)
    G = np.ones_like(t)
    with pytest.raises(ValueError, match="manual"):
        fit_maxwell_wiechert(t, G, method="manual")


def test_fit_three_mode_maxent_recovers_parameters():
    """MaxEnt auto-selection on a clean 3-mode signal should recover K=3
    and return τ values within 5 % of truth."""
    t = np.linspace(0.0, 100.0, 1024)
    G_inf_true, Gs, taus = 0.2, [1.5, 0.8, 0.3], [0.1, 1.0, 10.0]
    G = _synth(t, G_inf_true, Gs, taus, noise=1e-4)

    res = fit_maxwell_wiechert(t, G, method="maxent", max_n_modes=8)

    assert isinstance(res, MaxwellWiechertResult)
    assert res.n_modes == 3
    assert res.method == "maxent"
    assert res.residual < 1e-2

    # taus are returned slow-first (convention)
    assert res.tau_k[0] > res.tau_k[-1]

    # every truth τ should be matched within 5 %
    true_sorted = sorted(taus, reverse=True)
    for t_true, t_fit in zip(true_sorted, res.tau_k):
        assert abs(t_fit - t_true) / t_true < 0.05


def test_fit_variance_method_also_works():
    t = np.linspace(0.0, 100.0, 1024)
    G = _synth(t, 0.2, [1.0, 0.4], [0.5, 10.0], noise=1e-4)
    res = fit_maxwell_wiechert(t, G, method="variance", max_n_modes=6,
                               variance_threshold=0.9999)
    assert res.n_modes >= 2
    assert res.residual < 1e-2


def test_fit_manual_order_honoured():
    t = np.linspace(0.0, 50.0, 512)
    G = _synth(t, 0.0, [1.0, 0.5], [0.3, 3.0], noise=1e-5)
    res = fit_maxwell_wiechert(t, G, n_modes=2, method="manual")
    assert res.n_modes == 2


def test_fit_passes_explicit_G_inf():
    t = np.linspace(0.0, 20.0, 256)
    G = _synth(t, 0.5, [0.7], [1.0])
    res = fit_maxwell_wiechert(t, G, n_modes=1, method="manual", G_inf=0.5)
    assert res.G_inf == 0.5
    # The transient should have been fitted on (G - 0.5).
    assert abs(res.G_k[0] - 0.7) / 0.7 < 0.02
    assert abs(res.tau_k[0] - 1.0) / 1.0 < 0.02


def test_roundtrip_fit_then_predict():
    t = np.linspace(0.0, 100.0, 1024)
    G_true = _synth(t, 0.2, [1.5, 0.3], [0.5, 10.0], noise=1e-5)
    res = fit_maxwell_wiechert(t, G_true, method="maxent", max_n_modes=6)
    G_pred = evaluate_modulus(t, res.G_inf, res.G_k, res.tau_k)
    assert np.allclose(G_pred, G_true, atol=5e-3)
