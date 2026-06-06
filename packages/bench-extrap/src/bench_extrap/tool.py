"""Scaling-law fit + extrapolation."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Literal

import numpy as np

from hpc_triage import Problem, Tier, Verdict, VerdictStatus


# ──────────────────────────────────────────────────────────────────────────────
#  Generic scaling fit
# ──────────────────────────────────────────────────────────────────────────────

def fit_scaling_law(sizes: np.ndarray, times: np.ndarray,
                    model: Literal["power", "exp", "auto"] = "auto"
                    ) -> dict:
    """Fit either ``t = a · n^b`` (power law) or ``t = a · exp(b · n)``.

    Returns a dict with keys: ``model``, ``a``, ``b``, ``predict(n)``,
    ``r2``. When ``model='auto'``, returns whichever fits better in R².
    """
    sizes = np.asarray(sizes, dtype=float)
    times = np.asarray(times, dtype=float)
    if sizes.size != times.size or sizes.size < 3:
        raise ValueError("Need at least 3 (size, time) pairs")
    if np.any(sizes <= 0) or np.any(times <= 0):
        raise ValueError("sizes and times must be positive")

    def _power():
        # log(t) = log a + b log n
        b, log_a = np.polyfit(np.log(sizes), np.log(times), 1)
        a = float(np.exp(log_a))
        pred = a * sizes ** b
        ss_res = np.sum((times - pred) ** 2)
        ss_tot = np.sum((times - times.mean()) ** 2) or 1.0
        return {
            "model":  "power",
            "a":      a,
            "b":      float(b),
            "r2":     float(1 - ss_res / ss_tot),
            "predict": (lambda a_, b_: (lambda n: a_ * np.asarray(n, dtype=float) ** b_))(a, b),
        }

    def _exp():
        b, log_a = np.polyfit(sizes, np.log(times), 1)
        a = float(np.exp(log_a))
        pred = a * np.exp(b * sizes)
        ss_res = np.sum((times - pred) ** 2)
        ss_tot = np.sum((times - times.mean()) ** 2) or 1.0
        return {
            "model":  "exp",
            "a":      a,
            "b":      float(b),
            "r2":     float(1 - ss_res / ss_tot),
            "predict": (lambda a_, b_: (lambda n: a_ * np.exp(b_ * np.asarray(n, dtype=float))))(a, b),
        }

    fits = {"power": _power(), "exp": _exp()}
    if model == "power":
        return fits["power"]
    if model == "exp":
        return fits["exp"]
    # auto: pick higher R²
    return fits["power"] if fits["power"]["r2"] >= fits["exp"]["r2"] else fits["exp"]


# ──────────────────────────────────────────────────────────────────────────────
#  Tool
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class BenchExtrapTool:
    """Benchmark at 3 small sizes, extrapolate to the target."""

    runner: Callable[[Problem, int], float] | None = None  # returns wall_sec
    small_sizes: tuple[int, int, int] = (128, 256, 512)
    laptop_budget_sec: float = 60.0
    workstation_budget_sec: float = 600.0

    name: str = "bench-extrap"
    tier: Tier = Tier.LAPTOP

    def _default_runner(self, problem: Problem, n: int) -> float:
        """Default: measures time of a numpy-dense solve at size n.

        Used as a proxy when no external runner is injected. Represents
        the typical O(n²) cost of a dense ODE step for an n-dim system.
        """
        A = np.random.default_rng(0).standard_normal((n, n))
        start = time.perf_counter()
        np.linalg.solve(A + n * np.eye(n), np.ones(n))
        return time.perf_counter() - start

    def evaluate(self, problem: Problem) -> Verdict:
        runner = self.runner or self._default_runner
        target = int(problem.n_time_steps)

        sizes = np.array(self.small_sizes, dtype=float)
        times = np.array([runner(problem, int(s)) for s in sizes], dtype=float)

        try:
            fit = fit_scaling_law(sizes, times, model="auto")
        except Exception as exc:  # noqa: BLE001
            return Verdict(status=VerdictStatus.ABORT, tier=Tier.UNKNOWN,
                           message=f"Scaling fit failed: {exc!r}")

        predicted = float(fit["predict"](target))

        if predicted <= self.laptop_budget_sec:
            return Verdict(status=VerdictStatus.ESCALATE, tier=Tier.LAPTOP,
                           message=f"extrapolated {predicted:.1f}s at N={target} (laptop budget)",
                           cost_estimate_seconds=predicted,
                           diagnostic={"fit": {k: v for k, v in fit.items() if k != "predict"},
                                       "small_times": times.tolist()},
                           next_tool="memkern-ladder")
        if predicted <= self.workstation_budget_sec:
            return Verdict(status=VerdictStatus.ESCALATE, tier=Tier.WORKSTATION,
                           message=f"extrapolated {predicted:.1f}s — workstation recommended",
                           cost_estimate_seconds=predicted,
                           diagnostic={"fit": {k: v for k, v in fit.items() if k != "predict"}},
                           next_tool="local-dispatcher")
        return Verdict(status=VerdictStatus.ESCALATE, tier=Tier.HPC,
                       message=f"extrapolated {predicted:.1f}s — HPC required",
                       cost_estimate_seconds=predicted,
                       diagnostic={"fit": {k: v for k, v in fit.items() if k != "predict"}},
                       next_tool="hpc-manifest")


bench_extrap_tool = BenchExtrapTool()
