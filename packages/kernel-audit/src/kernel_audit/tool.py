"""Kernel-audit triage tool.

Classifies a Problem into a hardware tier based on the effective number
of Prony modes required to fit its bath correlation function.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from hpc_triage import Problem, Tier, Verdict, VerdictStatus
from memkern import maxent_select_order, prony_decompose


# ──────────────────────────────────────────────────────────────────────────────
#  Default tier thresholds — overridable per instance
# ──────────────────────────────────────────────────────────────────────────────

DEFAULT_LAPTOP_MAX_K = 10
DEFAULT_WORKSTATION_MAX_K = 50


# ──────────────────────────────────────────────────────────────────────────────
#  Bath correlation via FFT — inline, domain-agnostic
# ──────────────────────────────────────────────────────────────────────────────

def _bath_correlation(J, t_max: float, n_tau: int = 1024,
                      n_omega: int = 4096,
                      omega_max: float | None = None) -> tuple[np.ndarray, np.ndarray]:
    """C(τ) = ∫₀^∞ J(ω) · exp(-i ω τ) dω  (T=0 limit).

    Uses an FFT on a linear ω grid. For the triage use case we only
    need the shape of C(τ), not high-precision values.

    Returns
    -------
    tau : ndarray
        Uniform τ grid on [0, t_max].
    C : ndarray (complex)
        Bath correlation values on that grid.
    """
    if omega_max is None:
        # 10 × Nyquist for a t_max-wide τ grid is the safe default.
        omega_max = max(20.0 / max(t_max, 1.0), 10.0)
    omega = np.linspace(0.0, omega_max, n_omega)
    J_vals = np.asarray(J(omega), dtype=float)
    # Zero-temperature bath correlation on a τ grid by direct integration
    tau = np.linspace(0.0, t_max, n_tau)
    # C(τ) = ∫ J(ω) exp(-i ω τ) dω  — trapezoidal rule (fast, enough for triage)
    phases = np.exp(-1j * np.outer(tau, omega))           # (n_tau, n_omega)
    C = np.trapezoid(phases * J_vals[None, :], omega, axis=1)
    return tau, C


# ──────────────────────────────────────────────────────────────────────────────
#  The tool
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class KernelAuditTool:
    """Pre-flight audit of the bath spectral density.

    Attributes
    ----------
    laptop_max_K : int
        K above which we promote the verdict to WORKSTATION tier.
    workstation_max_K : int
        K above which we promote the verdict to HPC tier.
    entropy_threshold : float in (0, 1]
        MaxEnt entropy-ratio threshold passed to
        ``memkern.maxent_select_order``.
    max_probe_K : int
        Maximum order probed by the Prony decomposition during audit.
    n_tau : int
        τ-grid resolution for the bath correlation sample.
    """

    laptop_max_K: int = DEFAULT_LAPTOP_MAX_K
    workstation_max_K: int = DEFAULT_WORKSTATION_MAX_K
    entropy_threshold: float = 0.95
    max_probe_K: int = 60
    n_tau: int = 1024

    # TriageTool protocol attributes
    name: str = "kernel-audit"
    tier: Tier = Tier.LAPTOP

    def evaluate(self, problem: Problem) -> Verdict:
        # ── 1. Compute the bath correlation on a τ grid ──────────────────
        try:
            tau, C = _bath_correlation(
                problem.spectral_density,
                t_max=problem.t_max,
                n_tau=self.n_tau,
            )
        except Exception as exc:  # noqa: BLE001
            return Verdict(
                status=VerdictStatus.ABORT,
                tier=Tier.UNKNOWN,
                message=f"Could not sample J(ω): {exc!r}",
            )

        if not np.any(np.isfinite(C)) or np.all(np.abs(C) < 1e-14):
            return Verdict(
                status=VerdictStatus.ABORT,
                tier=Tier.UNKNOWN,
                message="Bath correlation is null or non-finite — check J(ω).",
            )

        # ── 2. Probe the Prony order via the SVD of the Hankel pencil ────
        try:
            probe = prony_decompose(tau, C, n_exp=self.max_probe_K)
        except Exception as exc:  # noqa: BLE001
            return Verdict(
                status=VerdictStatus.ABORT,
                tier=Tier.UNKNOWN,
                message=f"Prony probe failed: {exc!r}",
            )

        K = maxent_select_order(
            probe.singular_values,
            max_n_exp=self.max_probe_K,
            entropy_ratio_threshold=self.entropy_threshold,
        )

        # ── 3. Classify K → tier ─────────────────────────────────────────
        if K <= self.laptop_max_K:
            tier = Tier.LAPTOP
            flavour = f"laptop OK (K ≤ {self.laptop_max_K})"
        elif K <= self.workstation_max_K:
            tier = Tier.WORKSTATION
            flavour = f"workstation recommended (K in ({self.laptop_max_K}, {self.workstation_max_K}])"
        else:
            tier = Tier.HPC
            flavour = f"HPC likely (K > {self.workstation_max_K})"

        message = (
            f"J(ω) audit: effective K ≈ {K} modes — {flavour}. "
            f"Residual at K_max={self.max_probe_K}: {probe.residual:.2e}."
        )

        return Verdict(
            status=VerdictStatus.ESCALATE,
            tier=tier,
            message=message,
            diagnostic={
                "K_effective": int(K),
                "max_probe_K": int(self.max_probe_K),
                "probe_residual": float(probe.residual),
                "probe_variance_explained": float(probe.variance_explained),
                "singular_values": probe.singular_values,
                "entropy_threshold": float(self.entropy_threshold),
            },
            next_tool="memkern-ladder",
        )


# Ready-to-use default instance for `cascade()` ladders
kernel_audit_tool = KernelAuditTool()
