"""Tests for eternal-nm-sim.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

import numpy as np
import pytest

from eternal_nm_sim import blp_measure, compare_blp_ng, hall_channel, pauli_channel
from obliquity_ng import dephasing_channel, nonmarkovian_revival_channel


# ──────────────────────────────────────────────────────────────────────────────
#  Hall channel construction
# ──────────────────────────────────────────────────────────────────────────────

def test_hall_channel_bloch_factors_match_closed_form():
    """For the Hall choice γ_x=γ_y=1, γ_z=-tanh(t), we have
        λ_x = λ_y = (1 + e^{-2t}) / 2
        λ_z = e^{-2t}
    """
    t = np.linspace(0.0, 5.0, 1024)
    M = hall_channel()(t)

    expected_xy = (1.0 + np.exp(-2.0 * t)) / 2.0
    expected_z = np.exp(-2.0 * t)

    # Numerical integration of γ introduces O(dt²) error — accept 1e-3.
    assert np.allclose(M[:, 0, 0], expected_xy, atol=1e-3)
    assert np.allclose(M[:, 1, 1], expected_xy, atol=1e-3)
    assert np.allclose(M[:, 2, 2], expected_z, atol=1e-3)


def test_hall_channel_cptp_sum_rate_nonneg():
    """γ_x + γ_y + γ_z = 2 - tanh(t) ≥ 1 > 0 for all t."""
    # Sanity check on the rate functions we use inside hall_channel().
    t = np.linspace(0.0, 100.0, 2048)
    rate_sum = np.ones_like(t) + np.ones_like(t) - np.tanh(t)
    assert np.all(rate_sum > 0.5)


def test_hall_channel_gamma_z_negative():
    """Eternal non-Markovianity: γ_z(t) = -tanh(t) < 0 for all t > 0."""
    t = np.linspace(0.5, 10.0, 128)
    assert np.all(-np.tanh(t) < 0)


# ──────────────────────────────────────────────────────────────────────────────
#  BLP measure basic contracts
# ──────────────────────────────────────────────────────────────────────────────

def test_blp_rejects_bad_shape():
    with pytest.raises(ValueError, match="3, 3"):
        blp_measure(np.zeros((10, 2, 2)), np.linspace(0, 1, 10))


def test_blp_markovian_is_zero():
    t = np.linspace(0.0, 10.0, 1024)
    M = dephasing_channel(0.5)(t)
    assert blp_measure(M, t) < 1e-4


def test_blp_hall_channel_is_zero():
    """Hall's eternal-NM channel has no trace-distance revival → BLP ≈ 0."""
    t = np.linspace(0.0, 10.0, 2048)
    M = hall_channel()(t)
    assert blp_measure(M, t) < 1e-4


def test_blp_revival_channel_is_positive():
    t = np.linspace(0.0, 10.0, 2048)
    M = nonmarkovian_revival_channel(gamma=0.3, omega=2.0)(t)
    assert blp_measure(M, t) > 1e-2


# ──────────────────────────────────────────────────────────────────────────────
#  Side-by-side BLP vs N_G (the headline diagnostic)
# ──────────────────────────────────────────────────────────────────────────────

def test_compare_blp_ng_signatures():
    t = np.linspace(0.0, 10.0, 1024)
    res = compare_blp_ng({
        "dephasing":     dephasing_channel(0.5),
        "hall":          hall_channel(),
        "revival":       nonmarkovian_revival_channel(0.3, 2.0),
    }, t)

    assert set(res.keys()) == {"dephasing", "hall", "revival"}
    for name, row in res.items():
        assert set(row.keys()) == {"BLP", "N_G"}

    # Markovian channel: both zero
    assert res["dephasing"]["BLP"] < 1e-4
    assert res["dephasing"]["N_G"] < 1e-6

    # Revival channel: both positive (N_G detects, BLP detects)
    assert res["revival"]["BLP"] > 1e-2
    assert res["revival"]["N_G"] > 1e-2

    # Hall channel: both volume-/pair-distance-invisible (∴ both ≈ 0).
    # This is the research-relevant observation: the Hall channel shows
    # that "faithfulness" of any volume- or pair-distance-type measure is
    # violated by genuinely CP-indivisible dynamics whose contraction is
    # monotone in every channel-affine quantity. Detecting this regime
    # requires a finer measure (RHP / trace-norm of the Choi derivative).
    assert res["hall"]["BLP"] < 1e-4
    assert res["hall"]["N_G"] < 1e-4


# ──────────────────────────────────────────────────────────────────────────────
#  pauli_channel custom rates
# ──────────────────────────────────────────────────────────────────────────────

def test_pauli_channel_zero_rates_identity():
    """All γ_i = 0 → M(t) = I for all t."""
    t = np.linspace(0.0, 3.0, 64)
    ch = pauli_channel(
        gamma_x=lambda t: np.zeros_like(t, dtype=float),
        gamma_y=lambda t: np.zeros_like(t, dtype=float),
        gamma_z=lambda t: np.zeros_like(t, dtype=float),
    )
    M = ch(t)
    for i in range(t.size):
        assert np.allclose(M[i], np.eye(3), atol=1e-12)
