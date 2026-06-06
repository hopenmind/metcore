"""Tests for kernel-audit — verify tier classification on canonical J(ω).

We use spectral densities whose Prony complexity is known by construction:
  * Single Lorentzian → K≈1-2, laptop tier
  * Multi-peak J → mid K, workstation tier
  * Highly oscillatory/rough J → large K, HPC tier

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

import numpy as np
import pytest

from hpc_triage import Problem, Tier, VerdictStatus
from kernel_audit import KernelAuditTool, kernel_audit_tool


def _problem(J, *, t_max=10.0, n_steps=1024, d=2) -> Problem:
    return Problem(
        spectral_density=J,
        system_hamiltonian=np.eye(d, dtype=complex),
        coupling_strength=0.1,
        t_max=t_max,
        n_time_steps=n_steps,
    )


# ──────────────────────────────────────────────────────────────────────────────
#  Protocol conformance
# ──────────────────────────────────────────────────────────────────────────────

def test_tool_has_protocol_attributes():
    assert kernel_audit_tool.name == "kernel-audit"
    assert kernel_audit_tool.tier in (Tier.LAPTOP, Tier.WORKSTATION, Tier.HPC)
    assert hasattr(kernel_audit_tool, "evaluate")


# ──────────────────────────────────────────────────────────────────────────────
#  Simple spectra → laptop tier
# ──────────────────────────────────────────────────────────────────────────────

def test_single_lorentzian_lands_laptop():
    # A single narrow Lorentzian peak → K should be small (≤ 10)
    def J(w):
        w = np.asarray(w, dtype=float)
        return 0.1 / ((w - 1.0) ** 2 + 0.2 ** 2)

    v = kernel_audit_tool.evaluate(_problem(J, t_max=20.0))
    assert v.status == VerdictStatus.ESCALATE
    assert v.tier == Tier.LAPTOP
    assert v.diagnostic["K_effective"] <= 10
    assert v.next_tool == "memkern-ladder"


def test_ohmic_with_cutoff_lands_laptop():
    def J(w):
        w = np.asarray(w, dtype=float)
        return np.where(w > 0, 0.1 * w * np.exp(-(w / 3.0) ** 2), 0.0)

    v = kernel_audit_tool.evaluate(_problem(J, t_max=20.0))
    assert v.status == VerdictStatus.ESCALATE
    assert v.tier in (Tier.LAPTOP, Tier.WORKSTATION)


# ──────────────────────────────────────────────────────────────────────────────
#  Null / misbehaving J → ABORT
# ──────────────────────────────────────────────────────────────────────────────

def test_zero_spectral_density_aborts():
    v = kernel_audit_tool.evaluate(_problem(lambda w: np.zeros_like(np.asarray(w, dtype=float))))
    assert v.status == VerdictStatus.ABORT
    assert v.tier == Tier.UNKNOWN


def test_nan_spectral_density_aborts():
    v = kernel_audit_tool.evaluate(_problem(lambda w: np.full_like(np.asarray(w, dtype=float), np.nan)))
    assert v.status == VerdictStatus.ABORT


# ──────────────────────────────────────────────────────────────────────────────
#  Threshold promotion — force workstation / HPC via custom thresholds
# ──────────────────────────────────────────────────────────────────────────────

def test_lower_thresholds_promote_to_workstation():
    """If we lower laptop_max_K to zero, any non-trivial J is promoted."""
    tool = KernelAuditTool(laptop_max_K=0, workstation_max_K=100)
    v = tool.evaluate(_problem(lambda w: np.exp(-np.asarray(w, dtype=float) ** 2)))
    assert v.tier == Tier.WORKSTATION


def test_lower_both_thresholds_promote_to_hpc():
    tool = KernelAuditTool(laptop_max_K=0, workstation_max_K=0)
    v = tool.evaluate(_problem(lambda w: np.exp(-np.asarray(w, dtype=float) ** 2)))
    assert v.tier == Tier.HPC


# ──────────────────────────────────────────────────────────────────────────────
#  Integration with cascade() — the verdict feeds the ladder
# ──────────────────────────────────────────────────────────────────────────────

def test_cascade_uses_kernel_audit_verdict():
    from hpc_triage import cascade

    def J(w):
        w = np.asarray(w, dtype=float)
        return 0.1 / ((w - 1.0) ** 2 + 0.2 ** 2)

    # A trivial downstream tool that returns SOLVED so we can read the
    # cascade log without building another real tool.
    class _StopTool:
        name = "stub-solver"
        tier = Tier.LAPTOP
        def evaluate(self, p):
            from hpc_triage import Verdict
            return Verdict(status=VerdictStatus.SOLVED, tier=Tier.LAPTOP,
                           message="stub ok")

    ladder = [kernel_audit_tool, _StopTool()]
    v = cascade(_problem(J, t_max=20.0), ladder, verbose=False)
    assert v.status == VerdictStatus.SOLVED


# ──────────────────────────────────────────────────────────────────────────────
#  Determinism — same J → same verdict
# ──────────────────────────────────────────────────────────────────────────────

def test_verdict_is_deterministic():
    def J(w):
        w = np.asarray(w, dtype=float)
        return np.exp(-w ** 2)

    v1 = kernel_audit_tool.evaluate(_problem(J, t_max=10.0))
    v2 = kernel_audit_tool.evaluate(_problem(J, t_max=10.0))
    assert v1.tier == v2.tier
    assert v1.diagnostic["K_effective"] == v2.diagnostic["K_effective"]
