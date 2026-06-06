"""kernel-audit — pre-flight hardware-tier estimator for NZ problems.

Reads the spectral density J(ω) from a `hpc_triage.Problem`, computes a
bath correlation function C(τ) via FFT, fits a Matrix-Pencil Prony
decomposition, and asks `memkern.maxent_select_order` how many
exponential modes are actually necessary. The mode count K classifies
the problem into a hardware tier:

    K ≤ 10   → LAPTOP         (Prony-pseudomode fits comfortably)
    10 < K ≤ 50  → WORKSTATION (still tractable with ~64 GB RAM)
    K > 50   → HPC            (full HEOM / path-integral likely needed)

The tool always returns ``ESCALATE``: kernel-audit is a pre-flight
auditor, not a solver. The ``tier`` field of the returned ``Verdict``
is the hint the cascade downstream consumes.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

from kernel_audit.tool import KernelAuditTool, kernel_audit_tool

__all__ = ["KernelAuditTool", "kernel_audit_tool"]

__version__ = "0.1.0"
__author__ = "DESVAUX G.J.Y."
__contact__ = "contact@hopenmind.com"
__license__ = "Apache-2.0 OR LicenseRef-HopenMind-Commercial"
