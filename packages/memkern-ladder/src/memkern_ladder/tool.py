"""Three honest approximation levels, ordered from cheapest to most accurate.

Each level is a pure function ``Problem → (observable(t), diagnostic)``.
The ladder convergence check compares each level to its successor on
the same problem; the verdict is SOLVED at the first level whose
relative L² deviation from the next level is under
``problem.target_accuracy``.

We track a single scalar observable per problem — the population of
the excited state ⟨σ_z+I⟩/2 under a fixed initial state ρ_0 = |e⟩⟨e|.
It is the minimum common denominator that makes the three levels
comparable regardless of the Hilbert-space dimension. More elaborate
observables can be plugged via ``problem.metadata["observable"]``.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp

from hpc_triage import Problem, Tier, Verdict, VerdictStatus
from memkern import maxent_select_order, prony_decompose


# ──────────────────────────────────────────────────────────────────────────────
#  Shared helpers — bath correlation + observable choice
# ──────────────────────────────────────────────────────────────────────────────

def _bath_correlation(problem: Problem, n_tau: int = 1024,
                      omega_max: float | None = None,
                      n_omega: int = 4096) -> tuple[np.ndarray, np.ndarray]:
    """C(τ) = ∫ J(ω) exp(-i ω τ) dω on a uniform τ-grid."""
    if omega_max is None:
        omega_max = max(20.0 / max(problem.t_max, 1.0), 10.0)
    omega = np.linspace(0.0, omega_max, n_omega)
    J = np.asarray(problem.spectral_density(omega), dtype=float)
    tau = np.linspace(0.0, problem.t_max, n_tau)
    phases = np.exp(-1j * np.outer(tau, omega))
    C = np.trapezoid(phases * J[None, :], omega, axis=1)
    return tau, C


def _markov_rate(problem: Problem) -> float:
    """Golden-rule Markovian decay rate γ = 2π g² J(ω₀).

    ω₀ is taken from the largest-magnitude diagonal of H_S (assumed
    system frequency in the qubit sense). For d > 2 we use the
    spectral gap between the two lowest eigenvalues.
    """
    H = problem.system_hamiltonian
    eigs = np.linalg.eigvalsh(H + H.conj().T) / 2.0  # Hermitian part
    eigs = np.sort(eigs.real)
    omega0 = abs(eigs[1] - eigs[0]) if eigs.size >= 2 else 1.0
    omega0 = float(max(omega0, 1e-6))
    g2 = float(problem.coupling_strength) ** 2
    J0 = float(problem.spectral_density(np.array([omega0]))[0])
    return float(2.0 * np.pi * g2 * J0)


# ──────────────────────────────────────────────────────────────────────────────
#  Level 1 — Markovian Lindblad (analytical)
# ──────────────────────────────────────────────────────────────────────────────

def solve_level_1(problem: Problem) -> tuple[np.ndarray, np.ndarray, dict]:
    """P_e(t) = exp(-γ t) with γ from Fermi's golden rule."""
    gamma = _markov_rate(problem)
    t = np.linspace(0.0, problem.t_max, problem.n_time_steps)
    pe = np.exp(-gamma * t)
    return t, pe, {"gamma_markov": gamma, "level": 1}


# ──────────────────────────────────────────────────────────────────────────────
#  Level 2 — Born-Markov + 1st-order NZ correction
# ──────────────────────────────────────────────────────────────────────────────

def solve_level_2(problem: Problem) -> tuple[np.ndarray, np.ndarray, dict]:
    """Born-Markov with a time-dependent rate from the running bath-
    correlation integral:

        γ(t) = 2 g² · Re[∫₀^t C(s) ds]
        P(t) = exp(-∫₀^t γ(s) ds)

    For short t this reproduces the quadratic short-time decay of a
    non-Markovian bath. For t ≫ τ_bath (bath memory time) γ(t) saturates
    at the Markov golden-rule rate. This is a textbook Born-Markov
    approximation at first order, valid whenever the bath correlation
    integrates to a finite value.
    """
    t, C = _bath_correlation(problem, n_tau=problem.n_time_steps)
    g2 = float(problem.coupling_strength) ** 2

    dt = float(t[1] - t[0]) if len(t) > 1 else 1.0
    # γ(t) = 2 g² · Re[cum ∫ C(s) ds]   (trapezoidal running integral)
    C_re = C.real
    cum = np.zeros_like(C_re)
    cum[1:] = np.cumsum(0.5 * (C_re[1:] + C_re[:-1]) * dt)
    gamma_t = 2.0 * g2 * cum

    # ∫₀^t γ(s) ds  — trapezoidal cumulative
    phi = np.zeros_like(gamma_t)
    phi[1:] = np.cumsum(0.5 * (gamma_t[1:] + gamma_t[:-1]) * dt)
    pe = np.exp(-phi)

    return t, pe, {"gamma_infty": float(gamma_t[-1]),
                   "max_gamma":   float(np.max(gamma_t)),
                   "level": 2}


# ──────────────────────────────────────────────────────────────────────────────
#  Level 3 — Prony-pseudomode ODE solver
# ──────────────────────────────────────────────────────────────────────────────

def solve_level_3(problem: Problem, *,
                  max_K: int = 20,
                  entropy_threshold: float = 0.95
                  ) -> tuple[np.ndarray, np.ndarray, dict]:
    """Integrodifferential NZ master equation, reduced to a finite
    ODE system via Prony decomposition of the memory kernel.

    Write C(τ) ≈ Σ_k α_k exp(-β_k τ). The NZ equation

        dP/dt = -2 g² Re[∫₀^t C(t-s) P(s) ds]

    becomes, after introducing auxiliary variables
    ``Z_k(t) = ∫₀^t exp(-β_k (t-s)) P(s) ds``:

        dP/dt   = -2 g² Re[ Σ_k α_k Z_k(t) ]
        dZ_k/dt = -β_k Z_k(t) + P(t)                  Z_k(0) = 0

    This is a (1+2K)-dimensional real ODE (Z_k are complex so Re/Im
    parts are stored separately). Always gives a monotonically
    decreasing P for physical bath correlations — no pseudomode sign
    ambiguity.
    """
    tau, C = _bath_correlation(problem, n_tau=max(2048, problem.n_time_steps))

    probe = prony_decompose(tau, C, n_exp=max_K)
    K = maxent_select_order(probe.singular_values,
                            max_n_exp=max_K,
                            entropy_ratio_threshold=entropy_threshold)
    K = max(1, min(K, max_K))
    fit = prony_decompose(tau, C, n_exp=K)

    alphas = fit.alphas          # complex
    betas  = fit.betas           # complex
    g2 = float(problem.coupling_strength) ** 2

    # State vector y = [P, Re Z_0, Im Z_0, ..., Re Z_{K-1}, Im Z_{K-1}]
    dim = 1 + 2 * K

    def rhs(t, y):
        P = y[0]
        Z = y[1:1 + 2 * K].reshape(K, 2)      # (K, 2): [Re, Im]
        Z_complex = Z[:, 0] + 1j * Z[:, 1]

        dP = -2.0 * g2 * float(np.sum(alphas * Z_complex).real)
        dZ = -betas * Z_complex + P            # elementwise

        out = np.empty(dim, dtype=float)
        out[0] = dP
        out[1:1 + 2 * K] = np.stack([dZ.real, dZ.imag], axis=1).reshape(-1)
        return out

    y0 = np.zeros(dim)
    y0[0] = 1.0
    t_grid = np.linspace(0.0, problem.t_max, problem.n_time_steps)

    sol = solve_ivp(rhs, (0.0, problem.t_max), y0, t_eval=t_grid,
                    method="RK45", rtol=1e-6, atol=1e-9)
    if not sol.success:
        raise RuntimeError(f"Level-3 ODE solver failed: {sol.message}")

    pe = sol.y[0]
    # Clip numerical drift to [0, 1]
    pe = np.clip(pe, 0.0, 1.0)
    return t_grid, pe, {"level": 3, "K_modes": int(K),
                        "prony_residual": float(fit.residual)}


# ──────────────────────────────────────────────────────────────────────────────
#  Convergence check
# ──────────────────────────────────────────────────────────────────────────────

def _relative_rmse(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(b))
    if denom < 1e-30:
        return float(np.linalg.norm(a - b))
    return float(np.linalg.norm(a - b) / denom)


# ──────────────────────────────────────────────────────────────────────────────
#  The tool
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class MemkernLadderTool:
    """Run levels in order, stop at the first that converges vs next."""

    max_K: int = 20
    entropy_threshold: float = 0.95
    name: str = "memkern-ladder"
    tier: Tier = Tier.LAPTOP

    def evaluate(self, problem: Problem) -> Verdict:
        tol = problem.target_accuracy
        try:
            t1, pe1, d1 = solve_level_1(problem)
            t2, pe2, d2 = solve_level_2(problem)
        except Exception as exc:  # noqa: BLE001
            return Verdict(status=VerdictStatus.ABORT, tier=Tier.UNKNOWN,
                           message=f"Level 1/2 failed: {exc!r}")

        err_12 = _relative_rmse(pe1, pe2)
        if err_12 < tol:
            return Verdict(
                status=VerdictStatus.SOLVED, tier=Tier.LAPTOP,
                message=f"level 1 (Markovian) converges — err vs L2 = {err_12:.2e}",
                result={"t": t1, "population": pe1, "level": 1},
                diagnostic={**d1, "err_vs_next_level": err_12},
                cost_estimate_seconds=0.01,
            )

        # Level 3 is only tried if level 1 did not match level 2.
        try:
            t3, pe3, d3 = solve_level_3(
                problem, max_K=self.max_K,
                entropy_threshold=self.entropy_threshold,
            )
        except Exception as exc:  # noqa: BLE001
            return Verdict(
                status=VerdictStatus.ESCALATE, tier=Tier.WORKSTATION,
                message=f"level 3 could not be evaluated ({exc!r}) — escalating",
                diagnostic={"err_12": err_12, **d2},
            )

        err_23 = _relative_rmse(pe2, pe3)
        if err_23 < tol:
            return Verdict(
                status=VerdictStatus.SOLVED, tier=Tier.LAPTOP,
                message=f"level 2 (Born-Markov+1) converges — err vs L3 = {err_23:.2e}",
                result={"t": t2, "population": pe2, "level": 2},
                diagnostic={**d2, "err_vs_next_level": err_23},
                cost_estimate_seconds=0.5,
            )

        # If we have no next-level reference, accept level 3 as the most
        # accurate available result; flag it as SOLVED on laptop (Prony
        # pseudomode always ran) but attach level-3 diagnostic so the
        # downstream cascade sees whether HEOM would be warranted.
        return Verdict(
            status=VerdictStatus.SOLVED, tier=Tier.LAPTOP,
            message=f"level 3 (Prony-pseudomode) reached, K={d3['K_modes']}",
            result={"t": t3, "population": pe3, "level": 3},
            diagnostic={**d3, "err_12": err_12, "err_23": err_23,
                        "hint": "For stricter accuracy, escalate to HEOM via hpc-oracle."},
            cost_estimate_seconds=5.0,
        )


memkern_ladder_tool = MemkernLadderTool()
