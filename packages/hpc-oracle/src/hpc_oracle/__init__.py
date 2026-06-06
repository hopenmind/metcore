"""hpc-oracle — cost & memory oracle for NZ problems.

Given (d, K, t_max, N), predicts wall-time and peak RAM on four tiers
and reports which tier can accommodate the problem. Uses a simple
analytical cost model (dominant operations counted):

    Level-3 Prony-pseudomode:
        ODE dim       = 1 + 2K
        work per step ≈ (1 + 2K)²  (Jacobian-vector mult is dominant)
        steps         ≈ N  (user time grid)
        RAM bytes     ≈ 16 · (1 + 2K)²    (complex128 Jacobian)

    HEOM (for escalation sizing):
        aux operators ≈ (K + L_trunc) choose L_trunc    with L_trunc≈4
        ODE dim       = d² · n_aux
        RAM bytes     ≈ 16 · (d² · n_aux)²

The oracle is calibrated against a reference laptop (Intel i7-12700H,
16 GB), and scales linearly with nominal core speed. Exposed tier
parameters are overridable per instance for labs with different hardware.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

from hpc_oracle.tool import HPCOracleTool, estimate_cost, hpc_oracle_tool

__all__ = ["HPCOracleTool", "hpc_oracle_tool", "estimate_cost"]

__version__ = "0.1.0"
__author__ = "DESVAUX G.J.Y."
__license__ = "Apache-2.0 OR LicenseRef-HopenMind-Commercial"
