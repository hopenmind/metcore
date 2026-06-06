"""Core of the rheology adapter for ``memkern``.

The Maxwell-Wiechert (generalised Maxwell) model parameterises a linear
viscoelastic relaxation modulus as

    G(t) = G_∞ + Σ_k G_k · exp(-t/τ_k)          (1)

The dynamic moduli in the frequency domain follow by Fourier transform
of the Prony series:

    G'(ω) = G_∞ + Σ_k G_k · (ω τ_k)² / (1 + (ω τ_k)²)
    G''(ω) =       Σ_k G_k · (ω τ_k)   / (1 + (ω τ_k)²)

See e.g. Ferry, *Viscoelastic Properties of Polymers* (1980), chap. 3.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

import numpy as np

from memkern import PronyResult, maxent_select_order, prony_decompose


# ──────────────────────────────────────────────────────────────────────────────
#  Result container
# ──────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class MaxwellWiechertResult:
    """Result of a Maxwell-Wiechert fit.

    Attributes
    ----------
    G_inf : float
        Equilibrium (long-time plateau) modulus ``G_∞``. Units match the
        input ``G``.
    G_k : ndarray, shape (K,), real
        Transient-mode moduli, ``G_1, ..., G_K``.
    tau_k : ndarray, shape (K,), real
        Relaxation times ``τ_1, ..., τ_K`` in the units of the input
        ``t`` array.
    n_modes : int
        Number of retained Maxwell elements ``K``.
    residual : float
        Relative L² residual ``||G_data - G_fit||₂ / ||G_data||₂``.
    variance_explained : float
        Fraction of the transient signal energy captured. A value of 1.0
        would be a perfect fit of the non-DC part.
    method : str
        Order-selection method used, one of ``"maxent"``, ``"variance"``,
        ``"manual"``.
    raw : PronyResult
        Underlying memkern Prony result for advanced diagnostics.
    """

    G_inf: float
    G_k: np.ndarray
    tau_k: np.ndarray
    n_modes: int
    residual: float
    variance_explained: float
    method: str
    raw: PronyResult


# ──────────────────────────────────────────────────────────────────────────────
#  Forward model
# ──────────────────────────────────────────────────────────────────────────────

def evaluate_modulus(t: np.ndarray, G_inf: float,
                     G_k: np.ndarray, tau_k: np.ndarray) -> np.ndarray:
    """Evaluate ``G(t) = G_∞ + Σ G_k exp(-t/τ_k)`` on an array of times."""
    t = np.asarray(t, dtype=float)
    G_k = np.asarray(G_k, dtype=float)
    tau_k = np.asarray(tau_k, dtype=float)
    if G_k.shape != tau_k.shape:
        raise ValueError(f"G_k and tau_k must share shape: {G_k.shape} vs {tau_k.shape}")
    exponents = -np.outer(t, 1.0 / tau_k)
    return float(G_inf) + (G_k[None, :] * np.exp(exponents)).sum(axis=1)


def storage_loss_moduli(omega: np.ndarray, G_inf: float,
                        G_k: np.ndarray, tau_k: np.ndarray
                        ) -> tuple[np.ndarray, np.ndarray]:
    """Storage and loss moduli from a Prony series.

    Returns
    -------
    (G_storage, G_loss) : tuple of ndarrays
        ``G'(ω)`` and ``G''(ω)`` on the supplied ``omega`` grid.
    """
    omega = np.asarray(omega, dtype=float)
    G_k = np.asarray(G_k, dtype=float)
    tau_k = np.asarray(tau_k, dtype=float)
    wt = np.outer(omega, tau_k)                       # (nω, K)
    denom = 1.0 + wt ** 2
    G_storage = float(G_inf) + (G_k * (wt ** 2) / denom).sum(axis=1)
    G_loss = (G_k * wt / denom).sum(axis=1)
    return G_storage, G_loss


# ──────────────────────────────────────────────────────────────────────────────
#  Fit
# ──────────────────────────────────────────────────────────────────────────────

def _estimate_G_inf(t: np.ndarray, G: np.ndarray, tail_fraction: float = 0.05) -> float:
    """Estimate the long-time plateau modulus as the tail average."""
    n = max(4, int(len(G) * tail_fraction))
    return float(G[-n:].mean())


def fit_maxwell_wiechert(
    t: np.ndarray,
    G: np.ndarray,
    *,
    n_modes: Optional[int] = None,
    method: Literal["maxent", "variance", "manual"] = "maxent",
    G_inf: Optional[float] = None,
    max_n_modes: int = 16,
    maxent_threshold: float = 0.95,
    variance_threshold: float = 0.9999,
) -> MaxwellWiechertResult:
    """Fit a generalised Maxwell model to relaxation-modulus data.

    Parameters
    ----------
    t : ndarray, shape (N,)
        Uniform time grid (increasing, starts at 0).
    G : ndarray, shape (N,)
        Measured relaxation modulus ``G(t)`` — real, positive.
    n_modes : int or None
        Fix the number of Maxwell modes ``K``. If None, auto-select by
        ``method``.
    method : "maxent" | "variance" | "manual"
        Order-selection strategy when ``n_modes`` is None. ``"maxent"``
        uses ``memkern.maxent_select_order`` (NOVEL). ``"variance"`` is
        the conventional singular-value variance ratio. ``"manual"``
        requires ``n_modes`` to be given.
    G_inf : float or None
        Equilibrium modulus. If None, estimated as the tail-average of
        ``G(t)`` — suitable when the data covers at least a few
        relaxation times of the slowest mode.
    max_n_modes : int
        Upper cap on the number of modes when auto-selecting.
    maxent_threshold : float in (0, 1]
        Entropy-ratio threshold for MaxEnt selection.
    variance_threshold : float in (0, 1]
        Variance-ratio threshold for variance selection.

    Returns
    -------
    MaxwellWiechertResult

    Notes
    -----
    The function subtracts the estimated ``G_∞`` before calling the
    Prony routine, so the exponential sum is fitted on the pure
    transient. Negative recovered moduli are stable (they can arise
    from fitting noise), and very long recovered times (τ ≫ t_max) are
    interpreted as residual DC leakage and filtered when they exceed
    10× the time-window.
    """
    t = np.asarray(t, dtype=float)
    G = np.asarray(G, dtype=float)
    if t.ndim != 1 or G.ndim != 1 or t.shape != G.shape:
        raise ValueError("t and G must be 1-D arrays of equal length")
    if len(t) < 4:
        raise ValueError("need at least 4 samples")
    if method == "manual" and n_modes is None:
        raise ValueError('method="manual" requires n_modes to be specified')

    G_inf_used = float(G_inf) if G_inf is not None else _estimate_G_inf(t, G)
    y = G - G_inf_used

    # Phase 1 — get the Prony result (possibly with variance-ratio auto).
    if n_modes is None and method == "variance":
        raw = prony_decompose(t, y, variance_threshold=variance_threshold,
                              max_n_exp=max_n_modes)
    elif n_modes is None and method == "maxent":
        # First a wide variance-ratio fit to obtain the SVD spectrum, then
        # re-fit at the MaxEnt-chosen order.
        wide = prony_decompose(t, y, n_exp=max_n_modes)
        K = maxent_select_order(
            wide.singular_values,
            max_n_exp=max_n_modes,
            entropy_ratio_threshold=maxent_threshold,
        )
        raw = prony_decompose(t, y, n_exp=K)
    else:
        raw = prony_decompose(t, y, n_exp=n_modes)

    # Phase 2 — filter unphysical modes (τ ≫ window or τ ≤ 0).
    t_window = float(t[-1] - t[0])
    tau_cap = 10.0 * t_window if t_window > 0 else np.inf
    keep = (raw.betas.real > 0) & (1.0 / raw.betas.real < tau_cap)
    alphas = raw.alphas[keep].real
    betas = raw.betas[keep].real
    # Sort by decreasing relaxation time (slow first — rheology convention)
    order = np.argsort(-1.0 / betas) if betas.size else np.array([], dtype=int)
    G_k = alphas[order]
    tau_k = 1.0 / betas[order] if betas.size else betas

    return MaxwellWiechertResult(
        G_inf=G_inf_used,
        G_k=G_k,
        tau_k=tau_k,
        n_modes=int(G_k.size),
        residual=float(raw.residual),
        variance_explained=float(raw.variance_explained),
        method=method,
        raw=raw,
    )
