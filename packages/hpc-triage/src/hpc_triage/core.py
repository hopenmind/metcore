"""hpc-triage — the abstraction that triggers the cascade.

One problem type in, one verdict type out, one ladder. Every triage
tool (kernel-audit, memkern-ladder, hpc-oracle, bench-extrap,
cloud-dispatcher, hpc-manifest) implements exactly this contract:

    class Tool:
        name: str
        tier: Tier
        def evaluate(self, problem: Problem) -> Verdict: ...

The top-level ``cascade()`` runs the ladder in order and stops on the
first ``SOLVED`` / ``BLOCKED`` / ``ABORT``. An ``ESCALATE`` verdict
passes the same ``Problem`` to the next tool in the ladder. When every
tool escalates, the problem is confirmed HPC-bound — which is itself
a useful answer.

Why this file exists before the six tools do
─────────────────────────────────────────────
Putting the abstraction down first means:
  * Each tool is ~20 lines of pure domain logic (no orchestration).
  * Tools are independently testable with mocked Problems.
  * New tiers (e.g. a quantum emulator tier) slot in without
    touching existing tools.
  * The cascade itself is six lines, readable at a glance.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Protocol, runtime_checkable

import numpy as np


# ──────────────────────────────────────────────────────────────────────────────
#  Enums — hardware tiers and verdict-cascade states
# ──────────────────────────────────────────────────────────────────────────────

class Tier(str, Enum):
    """Hardware tier at which the problem is known (or believed) to fit.

    Ordered from cheapest to most expensive in compute hours.
    """
    LAPTOP       = "laptop"       # commodity i7/M2, ≤16 GB RAM
    WORKSTATION  = "workstation"  # threadripper or similar, 64–256 GB RAM
    GPU_CLOUD    = "gpu_cloud"    # single GPU on Modal/Colab/vast.ai
    HPC          = "hpc"          # multi-node SLURM/PBS cluster
    UNKNOWN      = "unknown"      # cost not estimated


class VerdictStatus(str, Enum):
    """What the cascade should do after this tool reports."""
    SOLVED   = "solved"     # problem answered at this tier — stop the cascade
    ESCALATE = "escalate"   # can't be solved here; try the next tool
    BLOCKED  = "blocked"    # no tier in the ladder can handle it
    ABORT    = "abort"      # bad input / internal error — human needed


# ──────────────────────────────────────────────────────────────────────────────
#  Problem — the single input type for every tool in the ladder
# ──────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Problem:
    """A non-Markovian open-quantum-system problem to triage.

    This is the minimum information any triage tool needs to decide
    whether a given hardware tier can solve the problem.

    Attributes
    ----------
    spectral_density : Callable[[np.ndarray], np.ndarray]
        J(ω). Called as ``J(omega_grid) -> values``.
    system_hamiltonian : np.ndarray
        The system's free Hamiltonian H_S (Hermitian, shape (d, d)).
    coupling_strength : float
        System-bath coupling g. Scalar is enough to pick a tier; full
        coupling operator can be attached via ``metadata`` if needed.
    temperature : float
        Bath temperature T (in frequency units; ℏ = k_B = 1). Default 0.
    t_max : float
        Target time horizon for the simulation.
    n_time_steps : int
        Time-grid resolution.
    target_accuracy : float
        Required relative accuracy on observables. Drives the choice of
        approximation tier (Markovian ok vs full HEOM needed).
    metadata : dict
        Free-form slot for tool-specific extras (Lindblad jump operators,
        initial state, etc.). Tools MAY read it; they MUST NOT require it.
    """
    spectral_density:    Callable[[np.ndarray], np.ndarray]
    system_hamiltonian:  np.ndarray
    coupling_strength:   float
    temperature:         float = 0.0
    t_max:               float = 10.0
    n_time_steps:        int   = 1024
    target_accuracy:     float = 1e-4
    metadata:            dict[str, Any] = field(default_factory=dict)

    def dimension(self) -> int:
        """Hilbert-space dimension d of the system."""
        return int(self.system_hamiltonian.shape[0])


# ──────────────────────────────────────────────────────────────────────────────
#  Verdict — the single output type for every tool in the ladder
# ──────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Verdict:
    """Outcome of one tool in the cascade.

    Attributes
    ----------
    status : VerdictStatus
        Drives the cascade.
    tier : Tier
        Hardware tier the tool considers adequate (or required).
    message : str
        One-line human-readable reason. Printed by ``cascade(verbose=True)``.
    cost_estimate_seconds : float or None
        Predicted wall-time at the stated ``tier``. ``None`` when the
        tool does not estimate cost.
    memory_estimate_gb : float or None
        Predicted peak memory at the stated ``tier``.
    result : Any
        The computed result if ``status == SOLVED``; ``None`` otherwise.
    diagnostic : dict
        Free-form tool-specific telemetry (singular spectrum, fit
        residuals, chosen order K, etc.). Used by downstream tools
        (e.g. ``hpc-manifest`` reads ``bench-extrap`` diagnostics to
        size the SLURM request).
    next_tool : str or None
        Hint to the cascade: if non-None, prefer escalating to this tool
        next (by ``name``). ``None`` means "use the natural ladder order".
    """
    status:                 VerdictStatus
    tier:                   Tier
    message:                str
    cost_estimate_seconds:  float | None = None
    memory_estimate_gb:     float | None = None
    result:                 Any | None = None
    diagnostic:             dict[str, Any] = field(default_factory=dict)
    next_tool:              str | None = None


# ──────────────────────────────────────────────────────────────────────────────
#  Protocol — what every tool must expose
# ──────────────────────────────────────────────────────────────────────────────

@runtime_checkable
class TriageTool(Protocol):
    """Every triage tool in the suite implements exactly this."""

    name: str
    tier: Tier

    def evaluate(self, problem: Problem) -> Verdict: ...


# ──────────────────────────────────────────────────────────────────────────────
#  The cascade itself — six readable lines
# ──────────────────────────────────────────────────────────────────────────────

_TERMINAL = (VerdictStatus.SOLVED, VerdictStatus.BLOCKED, VerdictStatus.ABORT)


def cascade(problem: Problem,
            ladder: list[TriageTool],
            *,
            verbose: bool = True,
            log: Callable[[str], None] | None = None) -> Verdict:
    """Run the ladder until a terminal verdict, or until exhausted.

    Parameters
    ----------
    problem : Problem
        The problem to triage.
    ladder : list of TriageTool
        Ordered from cheapest/fastest tier to most expensive. The cascade
        passes ``problem`` to each tool in turn.
    verbose : bool
        If True, each tool's verdict is logged.
    log : callable or None
        Custom log sink; defaults to ``print`` when ``verbose``.

    Returns
    -------
    Verdict
        The first terminal verdict, or a synthetic ``BLOCKED`` verdict
        confirming that HPC is required if every tool escalates.
    """
    sink = log or (print if verbose else (lambda _s: None))

    for tool in ladder:
        verdict = tool.evaluate(problem)
        if verbose:
            sink(f"[{tool.name:<22}] {verdict.status.value:<9} @ "
                 f"{verdict.tier.value:<12}  {verdict.message}")
        if verdict.status in _TERMINAL:
            return verdict
        # status == ESCALATE → keep going

    # Every tool escalated. This is itself a useful answer.
    return Verdict(
        status=VerdictStatus.BLOCKED,
        tier=Tier.HPC,
        message="Every triage tool escalated — problem confirmed HPC-bound.",
    )
