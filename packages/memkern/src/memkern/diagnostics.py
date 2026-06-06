"""
Kernel diagnostics - is the Markov Embedding Theorem even applicable here?

The MET requires a *rational* memory kernel, equivalently a memory correlation
C(τ) whose Hankel matrix has a finite numerical rank K (a clear gap in its
singular spectrum). When the spectrum instead decays as a power law (no gap),
the kernel is sub-ohmic / power-law: the finite MET fails and only the
ε-extension (K→∞, Hardy-space closure) applies.

This module turns that scope condition - flagged as the foremost reviewer attack
surface on the program - into an explicit, uncertainty-quantified verdict. It is
deliberately conservative: it would rather say "borderline, check by hand" than
wave a sub-ohmic kernel through as embeddable.

Public API
----------
hankel_singular_spectrum(tau, C)          -> singular values (descending)
embeddability_report(tau, C, ...)         -> structured verdict dict
bootstrap_order(tau, C, ...)              -> CI on K under measurement noise

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
Author: DESVAUX G.J.Y. - Hope 'n Mind SASU - Research
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np

from memkern.prony import maxent_select_order


def _hankel(C: np.ndarray) -> np.ndarray:
    """Square Hankel matrix H[i,j] = C[i+j] of maximal size from samples C."""
    n = C.size
    m = (n + 1) // 2
    idx = np.add.outer(np.arange(m), np.arange(m))
    return C[idx]


def hankel_singular_spectrum(tau: np.ndarray, C: np.ndarray) -> np.ndarray:
    """Descending singular values of the Hankel matrix of C(τ).

    The number of singular values above the noise floor is the auxiliary
    dimension K of the Markov embedding (Paper 1, Cor. 'Dimensional equivalence').
    """
    C = np.asarray(C)
    if np.iscomplexobj(C):
        C = np.abs(C)
    C = C.astype(float)
    H = _hankel(C)
    sv = np.linalg.svd(H, compute_uv=False)
    return np.sort(sv)[::-1]



def _rank_by_gap(sv: np.ndarray) -> tuple[int, float]:
    """Estimate the Hankel rank K as the location of the largest multiplicative
    drop in the singular spectrum (scale-invariant, noise-robust).

    Returns (K, gap_ratio) where gap_ratio = max_i sigma_i / sigma_{i+1}.
    A large gap_ratio is a clean rank cliff (rational/embeddable); a small one
    means the spectrum decays smoothly (power-law / sub-ohmic).
    """
    s = sv / sv[0]
    m = sv.size
    cut = int(np.count_nonzero(s > 1e-11))      # significant part
    cut = max(2, min(cut + 1, m))               # include one step into the floor
    seg = sv[:cut]
    ratios = seg[:-1] / np.maximum(seg[1:], 1e-300)
    j = int(np.argmax(ratios))
    return j + 1, float(ratios[j])


def _powerlaw_fit(sv: np.ndarray) -> tuple[float, float]:
    """Fit log(σ_i) = a·log(i) + b over the retained spectrum.

    Returns (slope, R²). A steep, high-R² slope with no gap is the signature
    of a power-law (sub-ohmic) spectrum; an exponential/rational spectrum
    breaks from the power-law line at the rank gap.
    """
    y = sv / sv[0]
    keep = y > 1e-12
    y = y[keep]
    if y.size < 4:
        return 0.0, 0.0
    x = np.log(np.arange(1, y.size + 1))
    ly = np.log(y)
    A = np.vstack([x, np.ones_like(x)]).T
    (slope, intercept), *_ = np.linalg.lstsq(A, ly, rcond=None)
    pred = A @ np.array([slope, intercept])
    ss_res = float(np.sum((ly - pred) ** 2))
    ss_tot = float(np.sum((ly - ly.mean()) ** 2)) or 1e-30
    r2 = 1.0 - ss_res / ss_tot
    return float(slope), float(r2)


def embeddability_report(
    tau: np.ndarray,
    C: np.ndarray,
    *,
    max_n_exp: int = 16,
    gap_cliff: float = 1.0e3,
    powerlaw_r2: float = 0.85,
    powerlaw_slope_max: float = -1.0,
) -> dict[str, Any]:
    """Decide whether C(τ) admits a finite Markov embedding, with diagnostics.

    Returns a dict with:
      regime          : "rational-embeddable" | "borderline" | "power-law/sub-ohmic"
      K_est           : estimated auxiliary dimension (finite-K guess)
      gap_ratio       : σ_K / σ_{K+1}  (large ⇒ clean rank gap ⇒ embeddable)
      n_eff           : effective number of modes (MaxEnt perplexity)
      powerlaw_slope  : log-log slope of the singular spectrum
      powerlaw_r2     : goodness of the power-law fit (high + no gap ⇒ sub-ohmic)
      advice          : human-readable scope verdict
    """
    tau = np.asarray(tau, dtype=float)
    C = np.asarray(C)
    if tau.size != C.size:
        return {"error": f"length mismatch: tau={tau.size}, C={C.size}"}
    if C.size < 8:
        return {"error": "need at least 8 samples for a Hankel diagnostic"}

    sv = hankel_singular_spectrum(tau, C)
    k, gap_ratio = _rank_by_gap(sv)
    p = sv ** 2 / np.sum(sv ** 2)
    p = p[p > 0]
    n_eff = float(np.exp(-np.sum(p * np.log(p))))
    slope, r2 = _powerlaw_fit(sv)

    clean_cliff = gap_ratio >= gap_cliff
    is_powerlaw = ((r2 >= powerlaw_r2) and (slope <= powerlaw_slope_max)
                   and (gap_ratio < gap_cliff))

    if clean_cliff and not is_powerlaw:
        regime = "rational-embeddable"
        advice = (f"Clean rank cliff at K={k} (σ_K/σ_K+1 = {gap_ratio:.3g}). "
                  f"The finite Markov Embedding Theorem applies; compile with "
                  f"Prony order {k}.")
    elif is_powerlaw:
        regime = "power-law/sub-ohmic"
        advice = (f"No rank gap; singular values follow a power law "
                  f"(slope {slope:.2f}, R²={r2:.2f}). The kernel is sub-ohmic: "
                  f"the FINITE MET does not apply - only the ε-extension "
                  f"(K→∞, Hardy closure). Treat any finite-K result as an "
                  f"approximation and report the truncation error.")
    else:
        regime = "borderline"
        advice = (f"Ambiguous: weak gap (σ_K/σ_K+1 = {gap_ratio:.1f} at K={k}) "
                  f"and partial power-law structure (R²={r2:.2f}). Increase the "
                  f"sampling/SNR, or verify K by an independent analytic Prony "
                  f"expansion before trusting the embedding.")

    return {
        "regime": regime,
        "K_est": k,
        "gap_ratio": gap_ratio,
        "n_eff": n_eff,
        "powerlaw_slope": slope,
        "powerlaw_r2": r2,
        "n_singular_values": int(sv.size),
        "singular_values_head": [float(x) for x in sv[:min(8, sv.size)]],
        "advice": advice,
    }


def bootstrap_order(
    tau: np.ndarray,
    C: np.ndarray,
    *,
    noise_rel: float = 0.02,
    n_boot: int = 200,
    seed: int = 0,
    max_n_exp: int = 16,
) -> dict[str, Any]:
    """Confidence interval on the embedding dimension K under measurement noise.

    Adds Gaussian noise of relative scale `noise_rel` to C and re-estimates K
    `n_boot` times. A K that is stable under noise is trustworthy; a K that
    scatters widely means the rank is not robustly identified by the data.
    """
    tau = np.asarray(tau, dtype=float)
    C = np.asarray(C)
    if np.iscomplexobj(C):
        C = np.abs(C)
    C = C.astype(float)
    rng = np.random.default_rng(seed)
    scale = noise_rel * float(np.max(np.abs(C)) or 1.0)
    ks = np.empty(n_boot, dtype=int)
    for b in range(n_boot):
        Cn = C + rng.normal(0.0, scale, size=C.shape)
        sv = hankel_singular_spectrum(tau, Cn)
        ks[b] = _rank_by_gap(sv)[0]
    lo, hi = np.percentile(ks, [2.5, 97.5])
    return {
        "K_median": int(np.median(ks)),
        "K_ci95": [int(lo), int(hi)],
        "K_mode": int(np.bincount(ks).argmax()),
        "stable": bool(int(lo) == int(hi)),
        "noise_rel": noise_rel,
        "n_boot": n_boot,
        "interpretation": (
            f"K = {int(np.median(ks))} (95% CI [{int(lo)},{int(hi)}]) under "
            f"{noise_rel*100:.0f}% noise - "
            + ("rank is robustly identified." if int(lo) == int(hi)
               else "rank is NOT robustly identified; collect cleaner data.")
        ),
    }
