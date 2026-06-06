"""Cost & memory oracle."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from hpc_triage import Problem, Tier, Verdict, VerdictStatus


# ──────────────────────────────────────────────────────────────────────────────
#  Tier profiles — overridable
# ──────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TierProfile:
    """Hardware profile for cost translation."""
    ram_gb:      float   # usable RAM
    rel_speed:   float   # relative wall-time factor vs reference laptop (1.0)


DEFAULT_PROFILES: dict[Tier, TierProfile] = {
    Tier.LAPTOP:       TierProfile(ram_gb=14.0,  rel_speed=1.0),
    Tier.WORKSTATION:  TierProfile(ram_gb=120.0, rel_speed=0.25),
    Tier.GPU_CLOUD:    TierProfile(ram_gb=24.0,  rel_speed=0.05),  # A100-class GPU; RAM = GPU VRAM
    Tier.HPC:          TierProfile(ram_gb=500.0, rel_speed=0.02),  # 64-128 cores node
}


# ──────────────────────────────────────────────────────────────────────────────
#  Cost model
# ──────────────────────────────────────────────────────────────────────────────

def _n_aux_heom(K: int, L_trunc: int = 4) -> int:
    """#auxiliary density operators in HEOM with given K / truncation."""
    return math.comb(K + L_trunc, L_trunc)


def estimate_cost(problem: Problem, *,
                  K: int | None = None,
                  method: str = "pseudomode",
                  profile: TierProfile | None = None,
                  ) -> dict:
    """Estimate wall-time and RAM of solving ``problem`` at a chosen tier.

    Parameters
    ----------
    problem : Problem
    K : int or None
        Effective Prony order. If None, a conservative ``K = 20`` is
        assumed; pass ``K`` from upstream ``kernel-audit`` for precision.
    method : "pseudomode" or "heom"
        Which level to size.
    profile : TierProfile or None
        Hardware profile. Defaults to laptop.
    """
    profile = profile or DEFAULT_PROFILES[Tier.LAPTOP]
    K = K if K is not None else 20

    d = problem.dimension()
    N = problem.n_time_steps

    if method == "pseudomode":
        ode_dim = 1 + 2 * K
        work = N * (ode_dim ** 2)
        ram_bytes = 16 * (ode_dim ** 2)
    elif method == "heom":
        n_aux = _n_aux_heom(K)
        ode_dim = d * d * n_aux
        work = N * (ode_dim ** 2)
        ram_bytes = 16 * (ode_dim ** 2)
    else:
        raise ValueError(f"Unknown method: {method!r}")

    # Reference: laptop does ~5·10^8 complex FLOP/s on dense matrices
    flops_ref = 5.0e8
    wall_sec = work / flops_ref * profile.rel_speed
    ram_gb = ram_bytes / 1024 ** 3

    return {
        "method":       method,
        "K":            K,
        "ode_dim":      ode_dim,
        "wall_seconds": float(wall_sec),
        "ram_gb":       float(ram_gb),
        "fits_tier":    ram_gb <= profile.ram_gb,
    }


# ──────────────────────────────────────────────────────────────────────────────
#  Tool
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class HPCOracleTool:
    """Chooses the cheapest tier where the problem fits + estimates cost."""

    profiles: dict = field(default_factory=lambda: dict(DEFAULT_PROFILES))
    name: str = "hpc-oracle"
    tier: Tier = Tier.LAPTOP

    def evaluate(self, problem: Problem) -> Verdict:
        # Get K from upstream diagnostics if available
        K = int(problem.metadata.get("K_effective", 20))
        estimates: dict[Tier, dict] = {}

        # Pseudomode: low-K problems
        for tier in (Tier.LAPTOP, Tier.WORKSTATION):
            estimates[tier] = estimate_cost(
                problem, K=K, method="pseudomode",
                profile=self.profiles[tier],
            )

        # HEOM: higher-K, might need workstation/HPC
        for tier in (Tier.WORKSTATION, Tier.GPU_CLOUD, Tier.HPC):
            estimates.setdefault(tier, estimate_cost(
                problem, K=K, method="heom",
                profile=self.profiles[tier],
            ))

        # Pick cheapest tier where it fits
        fits: list[Tier] = [t for t, est in estimates.items() if est["fits_tier"]]
        if not fits:
            return Verdict(
                status=VerdictStatus.BLOCKED, tier=Tier.HPC,
                message=(f"No tier accommodates K={K}, d={problem.dimension()} "
                         f"within target accuracy — problem may be infeasible."),
                diagnostic={"estimates": {t.value: e for t, e in estimates.items()},
                            "K_used": K},
            )
        # Preference order
        priority = [Tier.LAPTOP, Tier.WORKSTATION, Tier.GPU_CLOUD, Tier.HPC]
        best = next(t for t in priority if t in fits)
        est = estimates[best]

        status = VerdictStatus.ESCALATE if best != Tier.LAPTOP else VerdictStatus.ESCALATE
        return Verdict(
            status=status, tier=best,
            message=(f"{est['method']} at K={est['K']} fits {best.value} "
                     f"({est['ram_gb']:.2f} GB, ~{est['wall_seconds']:.1f}s)"),
            cost_estimate_seconds=est["wall_seconds"],
            memory_estimate_gb=est["ram_gb"],
            diagnostic={"estimates": {t.value: e for t, e in estimates.items()},
                        "K_used": K},
            next_tool="bench-extrap" if best != Tier.LAPTOP else "memkern-ladder",
        )


hpc_oracle_tool = HPCOracleTool()
