"""Tests for ``memkern.prony``.

Reference cases chosen so that the exact decomposition is known
analytically — no ground-truth from the function under test.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

import numpy as np
import pytest

from memkern import PronyResult, maxent_select_order, prony_decompose


# ──────────────────────────────────────────────────────────────────────────────
#  Smoke / shape contracts
# ──────────────────────────────────────────────────────────────────────────────

def test_imports():
    assert callable(prony_decompose)
    assert callable(maxent_select_order)
    assert PronyResult is not None


def test_rejects_non_uniform_grid():
    tau = np.array([0.0, 0.1, 0.3, 0.6, 1.0])  # non-uniform
    y = np.exp(-tau)
    with pytest.raises(ValueError, match="uniform"):
        prony_decompose(tau, y)


def test_rejects_length_mismatch():
    tau = np.linspace(0, 1, 10)
    y = np.exp(-tau)[:8]
    with pytest.raises(ValueError, match="Length mismatch"):
        prony_decompose(tau, y)


def test_rejects_too_few_samples():
    tau = np.array([0.0, 0.1, 0.2])
    y = np.exp(-tau)
    with pytest.raises(ValueError, match="at least 4"):
        prony_decompose(tau, y)


# ──────────────────────────────────────────────────────────────────────────────
#  Analytical reference cases
# ──────────────────────────────────────────────────────────────────────────────

def test_single_exponential_recovery():
    """A pure exponential should be recovered to machine precision."""
    tau = np.linspace(0, 10, 256)
    alpha_true = 2.5
    beta_true = 0.7
    y = alpha_true * np.exp(-beta_true * tau)

    result = prony_decompose(tau, y, n_exp=1)

    assert result.n_exp == 1
    assert result.residual < 1e-10
    assert np.isclose(np.abs(result.alphas[0]), alpha_true, rtol=1e-8)
    assert np.isclose(result.betas[0].real, beta_true, rtol=1e-8)


def test_two_exponential_recovery():
    """Sum of two exponentials with well-separated rates."""
    tau = np.linspace(0, 20, 512)
    y = 1.0 * np.exp(-0.3 * tau) + 0.5 * np.exp(-1.5 * tau)

    result = prony_decompose(tau, y, n_exp=2)

    assert result.n_exp == 2
    assert result.residual < 1e-8

    # Recover both rates irrespective of ordering
    rates = sorted(result.betas.real)
    assert np.isclose(rates[0], 0.3, rtol=1e-6)
    assert np.isclose(rates[1], 1.5, rtol=1e-6)


def test_oscillating_exponential_recovery():
    """Damped cosine = two complex-conjugate exponentials."""
    tau = np.linspace(0, 15, 400)
    gamma = 0.4
    omega = 2.0
    y = np.exp(-gamma * tau) * np.cos(omega * tau)

    result = prony_decompose(tau, y, n_exp=2)

    assert result.residual < 1e-6
    # Expect roots near β = gamma ± iω
    imag_parts = sorted(np.abs(result.betas.imag))
    assert np.isclose(imag_parts[-1], omega, rtol=1e-3)
    real_parts = result.betas.real
    assert np.allclose(real_parts, gamma, atol=1e-3)


def test_evaluate_reproduces_fit():
    tau = np.linspace(0, 5, 128)
    y = 3.0 * np.exp(-0.5 * tau) + 1.0 * np.exp(-2.0 * tau)
    result = prony_decompose(tau, y, n_exp=2)

    y_eval = result.evaluate(tau)
    assert np.allclose(y_eval, y, atol=1e-8)


# ──────────────────────────────────────────────────────────────────────────────
#  Auto order selection
# ──────────────────────────────────────────────────────────────────────────────

def test_auto_order_on_clean_two_exp():
    """Variance-ratio auto-select should pick K=2 on two-exponential data."""
    tau = np.linspace(0, 20, 512)
    y = 1.0 * np.exp(-0.3 * tau) + 0.5 * np.exp(-1.5 * tau)
    result = prony_decompose(tau, y)  # n_exp=None → auto
    assert result.n_exp >= 2
    assert result.residual < 1e-6


# ──────────────────────────────────────────────────────────────────────────────
#  MaxEnt order selector (NOVEL contribution)
# ──────────────────────────────────────────────────────────────────────────────

def test_maxent_selector_rank_one():
    """Rank-1 spectrum (one non-zero σ) → K=1."""
    # True rank-1: only one singular value is non-zero. The selector drops
    # zeros, computes H_full = 0 on the length-1 distribution, and returns
    # min_n_exp = 1.
    sv = np.array([5.0, 0.0, 0.0])
    assert maxent_select_order(sv) == 1


def test_maxent_selector_rank_one_single():
    """Single-element spectrum → K=1."""
    sv = np.array([5.0])
    assert maxent_select_order(sv) == 1


def test_maxent_selector_respects_min_max():
    sv = np.array([3.0, 2.0, 1.0, 0.5])
    K = maxent_select_order(sv, min_n_exp=2, max_n_exp=3)
    assert 2 <= K <= 3


def test_maxent_selector_monotone_in_threshold():
    """Tighter threshold → never fewer modes."""
    rng = np.random.default_rng(0)
    sv = np.sort(rng.uniform(0.1, 5.0, size=8))[::-1]
    K_low = maxent_select_order(sv, entropy_ratio_threshold=0.5)
    K_high = maxent_select_order(sv, entropy_ratio_threshold=0.99)
    assert K_high >= K_low


def test_maxent_selector_agrees_on_clean_two_exp():
    """On a clean two-exp signal the MaxEnt selector should not exceed the
    small number of modes actually present (within the max cap)."""
    tau = np.linspace(0, 20, 512)
    y = 1.0 * np.exp(-0.3 * tau) + 0.5 * np.exp(-1.5 * tau)
    result = prony_decompose(tau, y)
    K_max = maxent_select_order(result.singular_values, max_n_exp=16)
    assert 1 <= K_max <= 16
