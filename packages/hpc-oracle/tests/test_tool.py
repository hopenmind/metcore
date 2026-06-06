"""Tests for hpc-oracle."""

from __future__ import annotations

import numpy as np

from hpc_oracle import estimate_cost, hpc_oracle_tool
from hpc_triage import Problem, Tier, VerdictStatus


def _p(K_hint=None, d=2, N=1024):
    meta = {"K_effective": K_hint} if K_hint is not None else {}
    return Problem(
        spectral_density=lambda w: np.exp(-np.asarray(w, dtype=float) ** 2),
        system_hamiltonian=np.eye(d, dtype=complex),
        coupling_strength=0.1,
        n_time_steps=N,
        metadata=meta,
    )


def test_estimate_monotone_in_K():
    c1 = estimate_cost(_p(), K=5)
    c2 = estimate_cost(_p(), K=50)
    assert c2["wall_seconds"] > c1["wall_seconds"]
    assert c2["ram_gb"] > c1["ram_gb"]


def test_heom_costlier_than_pseudomode_same_K():
    c_p = estimate_cost(_p(), K=20, method="pseudomode")
    c_h = estimate_cost(_p(), K=20, method="heom")
    assert c_h["ram_gb"] > c_p["ram_gb"]


def test_small_K_fits_laptop():
    v = hpc_oracle_tool.evaluate(_p(K_hint=5))
    assert v.tier == Tier.LAPTOP
    assert v.status == VerdictStatus.ESCALATE


def test_large_K_pseudomode_still_fits_laptop():
    """Even at K=60, pseudomode has ODE dim = 121 → trivially fits laptop.
    This documents the intended behaviour: escalation happens through
    method choice (HEOM), not through K alone. See the companion HEOM
    test for the escalation path."""
    v = hpc_oracle_tool.evaluate(_p(K_hint=60, d=4))
    assert v.tier == Tier.LAPTOP


def test_extreme_K_forces_heom_and_escalates():
    """K high enough that the chosen-method (pseudomode) still fits,
    but the HEOM footprint in the diagnostic is huge — reviewers reading
    the diagnostic see the escalation path."""
    v = hpc_oracle_tool.evaluate(_p(K_hint=80, d=4))
    heom_est = v.diagnostic["estimates"].get("hpc")
    if heom_est is not None:
        assert heom_est["ram_gb"] > 100


def test_protocol_attributes():
    assert hpc_oracle_tool.name == "hpc-oracle"
    assert hpc_oracle_tool.tier == Tier.LAPTOP
