"""Tests for the geometric non-Markovianity measure N_G.

Negative controls: Markovian channels give N_G = 0 (faithfulness ⇒).
Positive control: an oscillating channel gives N_G > 0 (faithfulness ⇐).

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

import numpy as np
import pytest

from obliquity_ng import (
    amplitude_damping_channel,
    bloch_tetrahedron,
    dephasing_channel,
    depolarizing_channel,
    ng_from_bloch_matrices,
    ng_from_states,
    nonmarkovian_revival_channel,
)


# ──────────────────────────────────────────────────────────────────────────────
#  bloch_tetrahedron geometry
# ──────────────────────────────────────────────────────────────────────────────

def test_bloch_tetrahedron_on_unit_sphere():
    verts = bloch_tetrahedron()
    assert verts.shape == (4, 3)
    norms = np.linalg.norm(verts, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-12)


def test_bloch_tetrahedron_equidistant():
    verts = bloch_tetrahedron()
    pair_dists = np.linalg.norm(verts[:, None, :] - verts[None, :, :], axis=-1)
    off = pair_dists[~np.eye(4, dtype=bool)]
    # All six edges should have the same length
    assert np.allclose(off.min(), off.max(), atol=1e-12)


# ──────────────────────────────────────────────────────────────────────────────
#  Shape / arg validation
# ──────────────────────────────────────────────────────────────────────────────

def test_ng_from_bloch_matrices_wrong_shape():
    t = np.linspace(0, 1, 10)
    bad = np.zeros((10, 2, 2))
    with pytest.raises(ValueError, match="3, 3"):
        ng_from_bloch_matrices(bad, t)


def test_ng_from_bloch_matrices_length_mismatch():
    t = np.linspace(0, 1, 10)
    M = np.tile(np.eye(3), (8, 1, 1))
    with pytest.raises(ValueError, match="match M"):
        ng_from_bloch_matrices(M, t)


def test_ng_from_bloch_matrices_requires_two_samples():
    with pytest.raises(ValueError, match="at least 2"):
        ng_from_bloch_matrices(np.eye(3)[None, :, :], np.array([0.0]))


# ──────────────────────────────────────────────────────────────────────────────
#  Markovian channels: N_G = 0 (faithfulness)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("builder,gamma", [
    (dephasing_channel,         0.5),
    (depolarizing_channel,      0.7),
    (amplitude_damping_channel, 1.1),
])
def test_markovian_channels_zero_ng(builder, gamma):
    t = np.linspace(0.0, 10.0, 1024)
    channel = builder(gamma)
    M = channel(t)
    ng = ng_from_bloch_matrices(M, t)
    # Numerical gradient at the edges leaks a tiny positive amount; allow a
    # very small floor (≤ 1e-6 on a 1024-point grid).
    assert ng < 1e-6, f"expected ≈ 0, got {ng}"


def test_constant_channel_zero_ng():
    """Frozen channel (M = I for all t) trivially gives N_G = 0."""
    t = np.linspace(0.0, 5.0, 128)
    M = np.tile(np.eye(3), (t.size, 1, 1))
    ng = ng_from_bloch_matrices(M, t)
    assert ng < 1e-10


# ──────────────────────────────────────────────────────────────────────────────
#  Non-Markovian channel: N_G > 0 (faithfulness ⇐ direction)
# ──────────────────────────────────────────────────────────────────────────────

def test_revival_channel_positive_ng():
    t = np.linspace(0.0, 10.0, 2048)
    channel = nonmarkovian_revival_channel(gamma=0.3, omega=2.0)
    M = channel(t)
    ng = ng_from_bloch_matrices(M, t)
    assert ng > 1e-2, f"expected sizeable N_G for revival channel; got {ng}"


def test_revival_channel_ng_increases_with_longer_time():
    """Integrating over more oscillation periods should accumulate more
    positive-increment area."""
    channel = nonmarkovian_revival_channel(gamma=0.05, omega=3.0)

    t_short = np.linspace(0.0, 5.0, 2048)
    t_long = np.linspace(0.0, 15.0, 6144)

    ng_short = ng_from_bloch_matrices(channel(t_short), t_short)
    ng_long = ng_from_bloch_matrices(channel(t_long), t_long)
    assert ng_long > ng_short


# ──────────────────────────────────────────────────────────────────────────────
#  General-d path (ng_from_states) — qubit check agrees with Bloch path
# ──────────────────────────────────────────────────────────────────────────────

def _bloch_to_rho(r: np.ndarray) -> np.ndarray:
    """Map Bloch vector r to the density matrix ρ = (I + r·σ)/2."""
    sigma_x = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=complex)
    sigma_y = np.array([[0.0, -1j], [1j, 0.0]], dtype=complex)
    sigma_z = np.array([[1.0, 0.0], [0.0, -1.0]], dtype=complex)
    return 0.5 * (np.eye(2, dtype=complex)
                  + r[0] * sigma_x + r[1] * sigma_y + r[2] * sigma_z)


def test_ng_from_states_markovian_zero_general():
    t = np.linspace(0.0, 5.0, 256)
    channel = dephasing_channel(0.5)
    M_time = channel(t)                            # (T, 3, 3)

    verts = bloch_tetrahedron()                    # (4, 3)
    # Build states[i, k] = ρ_k evolved to t_i
    states = np.empty((t.size, 4, 2, 2), dtype=complex)
    for i in range(t.size):
        for k in range(4):
            r_k = M_time[i] @ verts[k]
            states[i, k] = _bloch_to_rho(r_k)

    ng = ng_from_states(states, t)
    assert ng < 1e-6


def test_ng_from_states_revival_matches_bloch_path():
    t = np.linspace(0.0, 6.0, 1024)
    channel = nonmarkovian_revival_channel(gamma=0.3, omega=2.0)
    M_time = channel(t)

    verts = bloch_tetrahedron()
    states = np.empty((t.size, 4, 2, 2), dtype=complex)
    for i in range(t.size):
        for k in range(4):
            states[i, k] = _bloch_to_rho(M_time[i] @ verts[k])

    ng_states = ng_from_states(states, t)
    ng_bloch = ng_from_bloch_matrices(M_time, t)
    assert ng_states > 1e-2
    assert ng_bloch > 1e-2
    # Two conceptually different routes should agree within a factor of 2.
    ratio = ng_states / max(ng_bloch, 1e-30)
    assert 0.5 < ratio < 2.0, f"paths disagree: bloch={ng_bloch}, states={ng_states}"
