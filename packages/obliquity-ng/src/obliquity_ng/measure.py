"""Geometric non-Markovianity measure N_G (Eq. 26).

For a qubit channel Φ_t represented on the Bloch sphere as

    r(t) = M(t) · r(0) + c(t)

(a 3×3 real affine map), the evolved-simplex volume satisfies

    V(t) = |det M(t)| · V(0) .

Hence

    N_G = ∫₀^∞  [ d/dt |det M(t)| ]_+  dt          (d=2 case, Eq. 26)

with the supremum over initial simplices achieved by the regular
tetrahedron inscribed in the Bloch sphere (Theorem 3.13.iii). Because
``|det M(t)|`` is independent of the affine translation c(t) and of
the specific simplex shape at d=2, the measure reduces to a simple
time integral.

For general d, use ``ng_from_states`` which takes a time-indexed set
of evolved density matrices, vectorises them in the Hilbert-Schmidt
basis, and computes the simplex volume from the determinant of the
edge matrix.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

import numpy as np


# ──────────────────────────────────────────────────────────────────────────────
#  Qubit simplex helper
# ──────────────────────────────────────────────────────────────────────────────

def bloch_tetrahedron() -> np.ndarray:
    """Return the four Bloch-vector vertices of the regular tetrahedron.

    The four vertices sit on the Bloch sphere (unit radius), are
    equidistant, and maximise the volume of any simplex inscribed in
    the sphere. Theorem 3.13.iii of the paper identifies this simplex
    as the supremum-achieving choice for N_G at d=2.

    Returns
    -------
    ndarray, shape (4, 3)
        Rows are Bloch vectors, ordered for reproducibility.
    """
    s = 1.0 / np.sqrt(3.0)
    return np.array([
        [ s,  s,  s],
        [ s, -s, -s],
        [-s,  s, -s],
        [-s, -s,  s],
    ])


# ──────────────────────────────────────────────────────────────────────────────
#  Qubit: NG from the Bloch-sphere affine matrix
# ──────────────────────────────────────────────────────────────────────────────

def ng_from_bloch_matrices(M: np.ndarray, t: np.ndarray,
                           *, atol: float = 1e-12) -> float:
    """Compute N_G for a qubit channel from its time-indexed Bloch map.

    Parameters
    ----------
    M : ndarray, shape (T, 3, 3)
        The affine 3×3 real matrix M(t) of the channel on the Bloch
        vector, evaluated on a time grid.
    t : ndarray, shape (T,)
        Monotone time grid (does not need to be uniform).
    atol : float
        Numerical floor below which increments are treated as zero.

    Returns
    -------
    float
        The measure N_G ≥ 0.
    """
    M = np.asarray(M, dtype=float)
    t = np.asarray(t, dtype=float)
    if M.ndim != 3 or M.shape[1:] != (3, 3):
        raise ValueError(f"M must have shape (T, 3, 3); got {M.shape}")
    if t.ndim != 1 or t.size != M.shape[0]:
        raise ValueError(f"t must match M[0]; got {t.shape} vs T={M.shape[0]}")
    if t.size < 2:
        raise ValueError("Need at least 2 time samples to compute N_G")

    volume = np.abs(np.linalg.det(M))          # V(t)/V(0), since M(0)=I in typical CPTP maps
    if volume[0] <= 0:
        raise ValueError("V(0) must be positive; got 0 (degenerate channel?)")

    dv_dt = np.gradient(volume, t)
    positive = np.where(dv_dt > atol, dv_dt, 0.0)
    integral = np.trapezoid(positive, t)
    return float(integral / volume[0])


# ──────────────────────────────────────────────────────────────────────────────
#  General d: NG from evolved density matrices
# ──────────────────────────────────────────────────────────────────────────────

def _vec(rho: np.ndarray) -> np.ndarray:
    """Hilbert-Schmidt vectorisation (real & imag parts stacked)."""
    flat = rho.reshape(-1)
    return np.concatenate([flat.real, flat.imag])


def _simplex_volume(vectors: np.ndarray) -> float:
    """Volume of the simplex with edges ``vectors`` (rows relative to v_0).

    ``vectors`` has shape (n-1, D); vertices are (0, v_1 - v_0, …, v_{n-1} - v_0)
    with dimension D = d² (or 2·d² if complex, stacked). We use an SVD-based
    volume formula that handles non-square shapes:

        V = sqrt(|det(V Vᵀ)|) / (n-1)!
    """
    vectors = np.asarray(vectors, dtype=float)
    if vectors.ndim != 2 or vectors.shape[0] == 0:
        return 0.0
    n_minus_1 = vectors.shape[0]
    gram = vectors @ vectors.T
    det = float(np.linalg.det(gram))
    # Due to noise, det may go slightly negative — clip.
    det = max(det, 0.0)
    return float(np.sqrt(det) / _factorial(n_minus_1))


def _factorial(n: int) -> float:
    out = 1.0
    for i in range(2, n + 1):
        out *= i
    return out


def ng_from_states(states: np.ndarray, t: np.ndarray,
                   *, atol: float = 1e-12) -> float:
    """Compute N_G for a general-d channel from evolved density matrices.

    Parameters
    ----------
    states : ndarray, shape (T, n, d, d)
        ``states[i, k]`` is ρ_k(t_i), the k-th initial state evolved to
        time ``t_i``. ``n >= d² + 1`` is recommended for a
        full-dimensional simplex; fewer states yield a lower-dimensional
        proxy.
    t : ndarray, shape (T,)
        Monotone time grid.
    atol : float
        Numerical floor below which increments are treated as zero.

    Returns
    -------
    float
        The measure N_G ≥ 0 for the simplex defined by the supplied states.
    """
    states = np.asarray(states, dtype=complex)
    t = np.asarray(t, dtype=float)
    if states.ndim != 4:
        raise ValueError(f"states must have shape (T, n, d, d); got {states.shape}")
    T, n, d_rows, d_cols = states.shape
    if d_rows != d_cols:
        raise ValueError("each state matrix must be square")
    if t.size != T:
        raise ValueError(f"t must match T={T}; got {t.size}")
    if n < 2:
        raise ValueError("need at least 2 initial states")

    volumes = np.empty(T, dtype=float)
    for i in range(T):
        vecs = np.stack([_vec(states[i, k]) - _vec(states[i, 0])
                         for k in range(1, n)])
        volumes[i] = _simplex_volume(vecs)

    if volumes[0] <= 0:
        raise ValueError("V(0) must be positive; increase `n` or choose a "
                         "non-degenerate initial simplex.")

    dv_dt = np.gradient(volumes, t)
    positive = np.where(dv_dt > atol, dv_dt, 0.0)
    integral = np.trapezoid(positive, t)
    return float(integral / volumes[0])
