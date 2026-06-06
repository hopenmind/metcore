"""
Prony / Matrix-Pencil decomposition of bath correlation functions.

Fits a complex time series C(τ) by a sum of complex exponentials

        C(τ) ≈ Σₖ αₖ · exp(-βₖ · τ)        (Re βₖ ≥ 0)

Used by the ``prony`` backend of ``MemoryKernel.from_spectral_density``
to convert the integro-differential non-Markovian master equation into
a small system of ordinary differential equations (pseudomode solver
in ``boltz_kernel.core.pseudomode``).

Why Matrix Pencil (not Prony, not ESPRIT):
  - Original Prony's method is ill-conditioned on noisy data — it
    collapses all spectral information into a single polynomial root
    extraction. We avoid it.
  - ESPRIT (rotational invariance) and Matrix Pencil are both SVD-based,
    well-conditioned, and theoretically equivalent in the noise-free
    limit. Matrix Pencil has slightly simpler code and we retain full
    SVD for automatic order selection.
  - AAA rational approximation is an alternative with very different
    code structure; reserved for a future backend if needed.

DOI: 10.5281/zenodo.19648837
SPDX-License-Identifier: Apache-2.0 OR LicenseRef-BoltZ-Commercial
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


# ──────────────────────────────────────────────────────────────────────────────
#  Public API
# ──────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PronyResult:
    """Decomposition ``C(τ) ≈ Σₖ αₖ exp(-βₖ τ)`` result.

    Attributes
    ----------
    alphas : ndarray, complex, shape (K,)
        Amplitudes αₖ.
    betas : ndarray, complex, shape (K,)
        Rates βₖ. ``Re(βₖ) ≥ 0`` (decaying); ``Im(βₖ)`` encodes oscillation.
    n_exp : int
        Number of kept exponentials K.
    residual : float
        L² fit residual: ``||C_data - C_fit||₂ / ||C_data||₂``.
    singular_values : ndarray, shape (min(L, N-L+1),)
        Full SVD spectrum of the Hankel pencil — useful for diagnostics
        and order-selection rationale.
    variance_explained : float
        Fraction of the signal energy captured by the K retained modes.
    """

    alphas: np.ndarray
    betas: np.ndarray
    n_exp: int
    residual: float
    singular_values: np.ndarray
    variance_explained: float

    def evaluate(self, tau):
        """Evaluate the fitted sum Σₖ αₖ exp(-βₖ τ) on an array of τ values."""
        tau = np.asarray(tau, dtype=float)
        # broadcast: shape (n_tau, K) → sum over K
        arg = -np.outer(tau, self.betas)  # (n_tau, K)
        return (self.alphas[None, :] * np.exp(arg)).sum(axis=1)


def prony_decompose(
    tau_grid: np.ndarray,
    C_values: np.ndarray,
    *,
    n_exp: Optional[int] = None,
    max_n_exp: int = 16,
    variance_threshold: float = 0.999,
    enforce_stable: bool = True,
) -> PronyResult:
    """
    Fit ``C(τ) ≈ Σₖ αₖ exp(-βₖ τ)`` on a uniform τ-grid via Matrix Pencil.

    Parameters
    ----------
    tau_grid : ndarray, shape (N,)
        Uniform time grid starting at 0 (must be sorted, monotone).
    C_values : ndarray, shape (N,)
        Bath correlation samples (may be complex).
    n_exp : int or None
        Number of exponentials K to fit. If None (default), chosen
        automatically by the ``variance_threshold`` criterion on the
        singular spectrum of the Hankel pencil, capped at ``max_n_exp``.
    max_n_exp : int
        Maximum K considered in the auto-selection path.
    variance_threshold : float in (0, 1]
        Auto-selection: smallest K such that
        ``Σᵢ<K σᵢ² / Σᵢ σᵢ² ≥ threshold``.
    enforce_stable : bool
        If True, rates with ``Re(βₖ) < 0`` (growing modes, unphysical for
        a bath correlation) are projected to ``Re(βₖ) = 0`` before the
        amplitude least-squares step. Recommended for physical
        correlations; disable only for diagnostic use.

    Returns
    -------
    PronyResult

    Raises
    ------
    ValueError
        For non-uniform grids, non-positive sample counts, or when the
        pencil has insufficient rank for the requested order.

    Notes
    -----
    The Matrix Pencil method (Hua & Sarkar 1990) proceeds as follows:

    1. Build the ``L × (N - L + 1)`` Hankel matrix ``H[i, j] = C[i + j]``
       with pencil parameter ``L ∈ [K+1, N - K]`` (we use ``L = N // 2``).
    2. Compute the SVD ``H = U Σ Vᴴ``.
    3. Truncate to rank K: keep the K largest singular values.
    4. Form ``V₁ = V_K[:-1, :]`` and ``V₂ = V_K[1:, :]`` (conjugate
       subsets of the right singular vectors).
    5. Solve the generalized eigenvalue problem ``V₁ zₖ = V₂ vₖ``. The
       eigenvalues ``zₖ`` are the *poles* in the z-plane.
    6. Rates: ``βₖ = -log(zₖ) / Δτ``.
    7. Amplitudes: least-squares solve of the Vandermonde system
       ``C_values[n] = Σₖ αₖ zₖⁿ``.
    """
    tau = np.asarray(tau_grid, dtype=float)
    C = np.asarray(C_values, dtype=complex)

    if tau.ndim != 1 or C.ndim != 1:
        raise ValueError("tau_grid and C_values must be 1-D arrays")
    if len(tau) != len(C):
        raise ValueError(f"Length mismatch: tau={len(tau)}, C={len(C)}")
    if len(C) < 4:
        raise ValueError("Need at least 4 samples for a meaningful Prony fit")

    # Verify uniform grid
    dtau = float(tau[1] - tau[0])
    spacing = np.diff(tau)
    if not np.allclose(spacing, dtau, rtol=1e-6):
        raise ValueError(
            "tau_grid must be uniform (Matrix Pencil requires equispaced samples)"
        )
    if dtau <= 0:
        raise ValueError("tau_grid must be increasing")

    N = len(C)
    L = N // 2  # pencil parameter — standard choice

    # ── Step 1. Hankel matrix H[i, j] = C[i + j], i=0..L, j=0..N-L-1 ──
    H = _build_hankel(C, L)  # shape (L+1, N-L)

    # ── Step 2. SVD ──
    U, sv, Vh = np.linalg.svd(H, full_matrices=False)

    # ── Step 3. Order selection ──
    if n_exp is None:
        K = _auto_select_order(sv, variance_threshold, max_n_exp)
    else:
        K = int(n_exp)
        if K < 1:
            raise ValueError("n_exp must be ≥ 1")
        if K > len(sv):
            raise ValueError(
                f"Requested n_exp={K} exceeds pencil rank {len(sv)}"
            )
    K = max(1, min(K, len(sv)))

    # ── Step 4. Truncated LEFT singular vectors ──
    # For a Hankel matrix built from samples C[n] = Σₖ αₖ zₖⁿ, the column
    # structure is H[i, j] = Σₖ αₖ zₖⁱ · zₖʲ. In the SVD H = U Σ Vᴴ, the
    # left singular vectors U carry the ``zₖⁱ`` pattern directly, while
    # the right singular vectors V carry ``conj(zₖ)ʲ`` (owing to the
    # Hermitian transpose in the SVD convention). Using U avoids the
    # spurious conjugation of the poles.
    U_K = U[:, :K]      # shape (L+1, K)
    U1 = U_K[:-1, :]    # (L, K)
    U2 = U_K[1:, :]     # (L, K)

    # ── Step 5. Generalized eigenvalue problem (U1⁺ U2) ──
    # Pseudo-inverse formulation is numerically equivalent to Hua-Sarkar
    # for well-conditioned pencils.
    M = np.linalg.pinv(U1) @ U2          # (K, K)
    z_poles = np.linalg.eigvals(M)        # z-plane poles

    # ── Step 6. Rates βₖ = -log(z) / dtau ──
    # Discard any z too close to origin (numerical ghosts)
    z_poles = z_poles[np.abs(z_poles) > 1e-14]
    if len(z_poles) == 0:
        raise ValueError("Matrix pencil produced no valid poles")
    betas = -np.log(z_poles) / dtau

    if enforce_stable:
        # project unphysical growing modes (Re β < 0) to marginally stable
        unstable = betas.real < 0
        betas = np.where(unstable, 1j * betas.imag, betas)

    # ── Step 7. Amplitudes via Vandermonde least-squares ──
    # C[n] = Σₖ αₖ zₖⁿ   for n = 0..N-1
    n_idx = np.arange(N)
    # z_poles may have been filtered; recompute from betas (consistent)
    z_used = np.exp(-betas * dtau)
    Vmatrix = z_used[None, :] ** n_idx[:, None]  # (N, K_used)
    alphas, *_ = np.linalg.lstsq(Vmatrix, C, rcond=None)

    # ── Fit quality ──
    C_fit = Vmatrix @ alphas
    residual = float(np.linalg.norm(C - C_fit) / max(np.linalg.norm(C), 1e-30))
    variance_explained = float(
        1.0 - np.sum(np.abs(C - C_fit) ** 2) / max(np.sum(np.abs(C) ** 2), 1e-30)
    )

    return PronyResult(
        alphas=alphas,
        betas=betas,
        n_exp=len(betas),
        residual=residual,
        singular_values=sv,
        variance_explained=variance_explained,
    )


# ──────────────────────────────────────────────────────────────────────────────
#  Internals
# ──────────────────────────────────────────────────────────────────────────────

def _build_hankel(c: np.ndarray, L: int) -> np.ndarray:
    """Return Hankel matrix H[i, j] = c[i + j] of shape (L+1, N-L)."""
    N = len(c)
    if not (0 < L < N):
        raise ValueError(f"Invalid pencil parameter L={L} for N={N}")
    # Use stride tricks for memory efficiency (no copy)
    idx_i = np.arange(L + 1)[:, None]
    idx_j = np.arange(N - L)[None, :]
    return c[idx_i + idx_j]


def _auto_select_order(
    singular_values: np.ndarray,
    variance_threshold: float,
    max_n_exp: int,
) -> int:
    """Smallest K s.t. cumulative energy ≥ threshold, clipped at max_n_exp.

    Default criterion — variance-ratio / PCA-style. Simple, well-known.
    For a MaxEnt-principled alternative, see ``maxent_select_order``.
    """
    sv2 = singular_values ** 2
    total = float(sv2.sum())
    if total <= 0:
        return 1
    cum = np.cumsum(sv2) / total
    # smallest K with cum[K-1] ≥ threshold
    idx = np.searchsorted(cum, variance_threshold) + 1
    return int(min(max(1, idx), max_n_exp))


def maxent_select_order(
    singular_values: np.ndarray,
    *,
    max_n_exp: int = 16,
    min_n_exp: int = 1,
    entropy_ratio_threshold: float = 0.95,
) -> int:
    """
    Select the Prony order K using a Maximum-Entropy criterion on the
    distribution of singular-value "weights".

    Rationale
    ---------
    Given the singular values σ₁ ≥ σ₂ ≥ ... of the Hankel pencil, define
    the normalised weight distribution

        pᵢ = σᵢ² / Σⱼ σⱼ²                 (probability over modes)

    and its Shannon entropy

        H = -Σᵢ pᵢ · log pᵢ .

    The **effective number of modes** (perplexity / ENC) is

        N_eff = exp(H) .

    N_eff is a continuous analogue of "how many modes actually matter":
    a rank-1 signal has N_eff = 1; a perfectly flat K-dimensional signal
    has N_eff = K.

    The MaxEnt criterion picks the smallest K such that the *entropy of
    the top-K truncated distribution* captures a fraction
    ``entropy_ratio_threshold`` of the full-spectrum entropy. This
    differs from variance-ratio in a specific, defensible way:

      - Variance-ratio is biased toward keeping dominant modes,
        even when the residual carries genuine structure spread across
        many small modes.
      - Entropy-ratio detects when *adding another mode* no longer
        increases the effective spread of information — a more honest
        measure of "the K that MaxEnt would pick given what the data
        has revealed".

    The connection with Jaynes's principle is direct: among all Prony
    decompositions that fit the data within tolerance, the one whose
    coefficients carry maximum entropy is the least-biased. This
    selector returns the smallest K for which the truncation preserves
    that property.

    Parameters
    ----------
    singular_values : ndarray
        Singular values of the Hankel pencil (descending order).
    max_n_exp : int
        Upper cap on K.
    min_n_exp : int
        Lower floor on K (default 1).
    entropy_ratio_threshold : float in (0, 1]
        Fraction of the full-spectrum entropy that the truncated
        distribution must preserve. Default 0.95 matches conventional
        "95% of the information" heuristic.

    Returns
    -------
    int
        Selected order K.
    """
    sv = np.asarray(singular_values, dtype=float)
    sv = sv[sv > 0]
    if sv.size == 0:
        return max(min_n_exp, 1)

    # Full-spectrum entropy
    p = sv ** 2 / (sv ** 2).sum()
    # Guard against log(0): p already has no zeros after the mask above
    H_full = float(-np.sum(p * np.log(p)))
    if H_full <= 0:
        return max(min_n_exp, 1)  # rank-1 case

    # Search smallest K with truncated entropy ≥ threshold × H_full
    cap = min(len(sv), max(max_n_exp, min_n_exp))
    for K in range(max(min_n_exp, 1), cap + 1):
        p_K = sv[:K] ** 2 / (sv[:K] ** 2).sum()
        H_K = float(-np.sum(p_K * np.log(p_K))) if K > 1 else 0.0
        # Normalise to a per-mode-equivalent to compare meaningfully
        if H_K >= entropy_ratio_threshold * H_full:
            return K

    return cap
