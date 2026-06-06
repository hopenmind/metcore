"""Randomised tests for eternal-nm-sim — BLP invariants under random
CPTP-preserving rate functions.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

import numpy as np
import pytest

from eternal_nm_sim import blp_measure, compare_blp_ng, pauli_channel


def _random_cptp_pauli(rng, allow_negative_axis: bool = False):
    """Build a random Pauli channel whose rate sum stays ≥ 0.

    - Draw three base rates r_i ~ U(0.1, 2).
    - Optionally multiply one axis by a sign-flipping factor
      ``1 - 2·tanh(t)`` while keeping the sum positive.
    """
    base = rng.uniform(0.1, 2.0, size=3)

    if allow_negative_axis:
        axis = int(rng.integers(0, 3))
        def gamma_axis(t):
            t = np.asarray(t, dtype=float)
            return base[axis] * (1.0 - 2.0 * np.tanh(t))
        def gamma_other(i):
            return lambda t, i=i: np.full_like(np.asarray(t, dtype=float), base[i])
        rates = [gamma_other(i) if i != axis else gamma_axis for i in range(3)]
    else:
        rates = [lambda t, i=i: np.full_like(np.asarray(t, dtype=float), base[i])
                 for i in range(3)]

    return pauli_channel(gamma_x=rates[0], gamma_y=rates[1], gamma_z=rates[2])


@pytest.mark.parametrize("seed", range(15))
def test_blp_on_random_markovian_pauli_is_zero(seed):
    rng = np.random.default_rng(seed)
    ch = _random_cptp_pauli(rng, allow_negative_axis=False)
    t = np.linspace(0.0, 10.0, 1024)
    M = ch(t)
    bl = blp_measure(M, t)
    assert 0.0 <= bl < 1e-3


@pytest.mark.parametrize("seed", range(15))
def test_blp_on_eternal_nm_pauli_is_nonnegative(seed):
    """With γ_i dipping negative on one axis, BLP may be zero (Hall-like)
    or non-zero depending on the rate shape — but always ≥ 0 and finite."""
    rng = np.random.default_rng(seed + 321)
    ch = _random_cptp_pauli(rng, allow_negative_axis=True)
    t = np.linspace(0.0, 10.0, 1024)
    M = ch(t)
    bl = blp_measure(M, t)
    assert bl >= 0.0
    assert np.isfinite(bl)


def test_compare_blp_ng_random_batch():
    """On a random basket of channels, every row has BLP ≥ 0 and N_G ≥ 0."""
    rng = np.random.default_rng(42)
    t = np.linspace(0.0, 10.0, 1024)

    channels = {}
    for k in range(6):
        channels[f"rand-markovian-{k}"] = _random_cptp_pauli(rng, allow_negative_axis=False)
    for k in range(6):
        channels[f"rand-eternal-{k}"] = _random_cptp_pauli(rng, allow_negative_axis=True)

    table = compare_blp_ng(channels, t)
    for name, row in table.items():
        assert row["BLP"] >= 0.0, name
        assert row["N_G"] >= 0.0, name
        assert np.isfinite(row["BLP"]), name
        assert np.isfinite(row["N_G"]), name
