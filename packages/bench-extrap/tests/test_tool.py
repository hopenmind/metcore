"""Tests for bench-extrap."""

from __future__ import annotations

import numpy as np
import pytest

from bench_extrap import BenchExtrapTool, bench_extrap_tool, fit_scaling_law
from hpc_triage import Problem, Tier, VerdictStatus


def _problem(N=1024):
    return Problem(
        spectral_density=lambda w: np.exp(-np.asarray(w, dtype=float) ** 2),
        system_hamiltonian=np.eye(2, dtype=complex),
        coupling_strength=0.1,
        n_time_steps=N,
    )


def test_fit_power_law_exact():
    sizes = np.array([10.0, 100.0, 1000.0])
    times = 2.0 * sizes ** 3
    f = fit_scaling_law(sizes, times, model="power")
    assert f["model"] == "power"
    assert abs(f["b"] - 3.0) < 1e-6
    assert abs(f["a"] - 2.0) < 1e-6
    assert f["r2"] > 0.999


def test_fit_exp_law_exact():
    sizes = np.array([1.0, 2.0, 3.0])
    times = np.exp(1.5 * sizes)
    f = fit_scaling_law(sizes, times, model="exp")
    assert f["model"] == "exp"
    assert abs(f["b"] - 1.5) < 1e-6
    assert f["r2"] > 0.999


def test_fit_auto_picks_best():
    # Power-law data → auto should pick power
    sizes = np.array([10.0, 100.0, 1000.0])
    times = sizes ** 2
    f = fit_scaling_law(sizes, times, model="auto")
    assert f["model"] == "power"


def test_fit_rejects_too_few_points():
    with pytest.raises(ValueError, match="at least 3"):
        fit_scaling_law(np.array([1.0]), np.array([1.0]))


def test_fit_rejects_nonpositive():
    with pytest.raises(ValueError, match="positive"):
        fit_scaling_law(np.array([1.0, 2.0, 3.0]), np.array([1.0, -2.0, 3.0]))


def test_tool_protocol_attributes():
    assert bench_extrap_tool.name == "bench-extrap"
    assert bench_extrap_tool.tier == Tier.LAPTOP


def test_tool_with_synthetic_runner_fast_problem():
    """Injected runner that reports tiny times → laptop verdict."""
    tool = BenchExtrapTool(
        runner=lambda p, n: 1e-6 * (n ** 2),   # O(n²), very fast
        small_sizes=(50, 100, 200),
    )
    v = tool.evaluate(_problem(N=500))
    assert v.status == VerdictStatus.ESCALATE
    assert v.tier == Tier.LAPTOP


def test_tool_with_slow_runner_escalates():
    """Injected runner that scales exponentially → HPC verdict."""
    tool = BenchExtrapTool(
        runner=lambda p, n: 1e-4 * np.exp(0.05 * n),
        small_sizes=(10, 20, 30),
    )
    v = tool.evaluate(_problem(N=500))   # huge exp blowup
    assert v.tier == Tier.HPC


def test_default_runner_is_callable():
    tool = BenchExtrapTool(small_sizes=(16, 32, 64))
    v = tool.evaluate(_problem(N=128))
    assert v.status == VerdictStatus.ESCALATE
    assert v.cost_estimate_seconds is not None
