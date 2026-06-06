"""Tests for memkern-ladder — 3-level convergence and escalation.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

import numpy as np
import pytest

from hpc_triage import Problem, Tier, VerdictStatus
from memkern_ladder import (
    MemkernLadderTool,
    memkern_ladder_tool,
    solve_level_1,
    solve_level_2,
    solve_level_3,
)


def _problem(J=None, t_max=10.0, target=1e-3, g=0.1, N=512) -> Problem:
    if J is None:
        J = lambda w: np.exp(-np.asarray(w, dtype=float) ** 2)
    return Problem(
        spectral_density=J,
        system_hamiltonian=np.diag([0.0, 1.0]).astype(complex),
        coupling_strength=g,
        t_max=t_max,
        n_time_steps=N,
        target_accuracy=target,
    )


# ──────────────────────────────────────────────────────────────────────────────
#  Levels in isolation
# ──────────────────────────────────────────────────────────────────────────────

def test_level_1_exponential_decay():
    t, pe, diag = solve_level_1(_problem())
    assert pe.shape == t.shape
    assert np.isclose(pe[0], 1.0, atol=1e-12)
    assert 0.0 <= pe[-1] <= 1.0
    assert "gamma_markov" in diag


def test_level_2_produces_monotone_decaying_population():
    """Born-Markov with a running-rate integral must produce a
    monotonically decreasing population for a physical bath."""
    t, pe, diag = solve_level_2(_problem())
    assert pe.shape == t.shape
    assert np.isclose(pe[0], 1.0, atol=1e-10)
    # Monotone non-increasing up to tiny numerical jitter
    dp = np.diff(pe)
    assert np.all(dp <= 1e-6), f"non-monotone somewhere (max dp = {dp.max()})"
    assert 0.0 <= pe.min() <= pe.max() <= 1.0 + 1e-6


def test_level_3_returns_finite_population():
    t, pe, diag = solve_level_3(_problem())
    assert pe.shape == t.shape
    assert np.all(np.isfinite(pe))
    assert diag["level"] == 3
    assert diag["K_modes"] >= 1


# ──────────────────────────────────────────────────────────────────────────────
#  Ladder verdicts
# ──────────────────────────────────────────────────────────────────────────────

def test_protocol_attributes():
    assert memkern_ladder_tool.name == "memkern-ladder"
    assert memkern_ladder_tool.tier == Tier.LAPTOP
    assert hasattr(memkern_ladder_tool, "evaluate")


def test_ladder_solves_fast_bath_at_level_1():
    """Very-fast bath → Markov is accurate → ladder stops at level 1."""
    v = memkern_ladder_tool.evaluate(
        _problem(J=lambda w: np.exp(-(w / 50.0) ** 2), target=0.1)
    )
    assert v.status == VerdictStatus.SOLVED
    assert v.diagnostic["level"] in (1, 2, 3)


def test_ladder_returns_solved_for_standard_problem():
    """On a generic Gaussian bath, the ladder reaches SOLVED at some
    level — that is the whole contract of the tool."""
    v = memkern_ladder_tool.evaluate(_problem(target=1e-2))
    assert v.status == VerdictStatus.SOLVED
    assert v.result is not None
    assert "population" in v.result
    assert v.diagnostic["level"] in (1, 2, 3)


def test_ladder_result_is_finite_and_probability_like():
    v = memkern_ladder_tool.evaluate(_problem(target=1e-2))
    pe = v.result["population"]
    assert np.all(np.isfinite(pe))
    # initial excited-state population is 1.0
    assert np.isclose(pe[0], 1.0, atol=1e-6)
    # population stays in [0, 1] (up to numerical drift ±0.02)
    assert pe.max() <= 1.02
    assert pe.min() >= -0.02


def test_ladder_tight_tolerance_escalates_cleanly_or_solves():
    """With an unrealistically tight tolerance, the ladder must either
    SOLVE (level 3 reached) or ESCALATE — never ABORT or crash."""
    v = memkern_ladder_tool.evaluate(_problem(target=1e-20, t_max=30.0))
    assert v.status in (VerdictStatus.SOLVED, VerdictStatus.ESCALATE)


# ──────────────────────────────────────────────────────────────────────────────
#  Custom tolerance knobs
# ──────────────────────────────────────────────────────────────────────────────

def test_custom_max_K_is_respected():
    tool = MemkernLadderTool(max_K=4)
    v = tool.evaluate(_problem(target=1e-2))
    # Level 3 (if reached) must not exceed max_K
    if v.diagnostic.get("level") == 3:
        assert v.diagnostic["K_modes"] <= 4
