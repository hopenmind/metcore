"""Domain-agnostic demo: Maxwell–Wiechert (generalised Maxwell) relaxation.

Purpose
-------
Demonstrate that ``memkern`` is not quantum-specific. The same Matrix-Pencil
Prony decomposition that fits a bath correlation function ``C(τ)`` in an
open-quantum-system kernel fits the relaxation modulus of a viscoelastic
material:

    G(t) = G_∞ + Σ_k G_k · exp(-t/τ_k)        (rheology, Prony series)

This is literally the same ``Σ_k α_k exp(-β_k t)`` with a DC offset. The
recovery test below uses known moduli ``G_k`` and relaxation times ``τ_k``,
synthesises ``G(t)``, adds a tiny noise floor, and reconstructs the
parameters blind with ``memkern.prony_decompose``.

Run
---
    uv run python packages/memkern/examples/maxwell_wiechert.py

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

import numpy as np

from memkern import maxent_select_order, prony_decompose


def _truth():
    """Three-element Maxwell–Wiechert model with a DC floor.

    Returns ``(G_inf, G_list, tau_list)``. Parameters are representative
    of a typical polymer-melt relaxation spectrum spanning two decades.
    """
    G_inf = 0.2           # DC / equilibrium modulus  [arb]
    G_list = [1.5, 0.8, 0.3]        # transient moduli
    tau_list = [0.1, 1.0, 10.0]     # relaxation times
    return G_inf, G_list, tau_list


def _synthesise(t: np.ndarray, G_inf: float, Gs, taus, noise: float = 0.0):
    y = np.full_like(t, G_inf, dtype=float)
    for G_k, tau_k in zip(Gs, taus):
        y += G_k * np.exp(-t / tau_k)
    if noise > 0:
        y = y + noise * np.random.default_rng(0).standard_normal(t.shape)
    return y


def main() -> int:
    # Uniform grid on [0, 100] — covers the slow τ=10 relaxation by 10×.
    t = np.linspace(0.0, 100.0, 1024)
    G_inf_true, Gs_true, taus_true = _truth()
    y = _synthesise(t, G_inf_true, Gs_true, taus_true, noise=1e-4)

    # Subtract a DC estimate so Prony sees a pure exponential sum.
    # (The equilibrium modulus G_∞ is the long-time plateau of G(t).)
    G_inf_est = float(y[-32:].mean())
    y_centred = y - G_inf_est

    # Blind decomposition — auto order via variance ratio
    result = prony_decompose(t, y_centred, variance_threshold=0.9999)
    K_variance = result.n_exp

    # Independent MaxEnt order pick from the singular spectrum
    K_maxent = maxent_select_order(result.singular_values,
                                   max_n_exp=8,
                                   entropy_ratio_threshold=0.95)

    # Format results
    rates_recovered = sorted(result.betas.real)
    rates_true = sorted(1.0 / tau for tau in taus_true)

    width = 66
    print("=" * width)
    print("Maxwell–Wiechert recovery via memkern.prony_decompose")
    print("=" * width)
    print(f"Grid:                 N = {t.size}, t ∈ [{t.min():.2f}, {t.max():.2f}]")
    print(f"Noise floor:          σ = 1e-4 (Gaussian)")
    print(f"G_∞ true / estimated: {G_inf_true:.4f} / {G_inf_est:.4f}")
    print("-" * width)
    print(f"K auto (variance ≥ 0.9999):  {K_variance}")
    print(f"K MaxEnt   (entropy ≥ 0.95): {K_maxent}")
    print(f"Truth K:                     {len(taus_true)}")
    print("-" * width)
    print(f"{'Rate β_k (true)':>24} │ {'Rate β_k (recovered)':>24}")
    print("-" * width)
    for i in range(max(len(rates_true), len(rates_recovered))):
        t_str = f"{rates_true[i]:.6f}" if i < len(rates_true) else "—"
        r_str = f"{rates_recovered[i]:.6f}" if i < len(rates_recovered) else "—"
        tau_true = f"τ={1/rates_true[i]:.3f}" if i < len(rates_true) else ""
        tau_rec = f"τ={1/rates_recovered[i]:.3f}" if (
            i < len(rates_recovered) and rates_recovered[i] > 1e-12
        ) else ""
        print(f"{t_str:>14} ({tau_true:>8}) │ {r_str:>14} ({tau_rec:>8})")
    print("-" * width)
    print(f"Relative L² residual:  {result.residual:.3e}")
    print(f"Variance explained:    {result.variance_explained:.6f}")
    print("=" * width)

    # Acceptance: at least the true three rates should be within 2 %
    # of the recovered rates (allowing spurious modes on top).
    hits = 0
    for rt in rates_true:
        if any(abs(rr - rt) / rt < 2e-2 for rr in rates_recovered):
            hits += 1
    ok = hits == len(rates_true)
    print(f"\nAcceptance: {hits}/{len(rates_true)} true rates matched within 2%.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
