"""
Memory kernel computation from spectral densities.

Core class: MemoryKernel
  - from_spectral_density(J, g, T, omega0) → MemoryKernel
  - from_bath_correlation(C, T) → MemoryKernel
  - evaluate(t, s) → float
  - solve(rho0, tspan) → Result

DOI: 10.5281/zenodo.19648837 | ORCID: 0009-0008-9813-4627
SPDX-License-Identifier: Apache-2.0 OR LicenseRef-BoltZ-Commercial
"""

import os
import warnings
import numpy as np
from scipy.fft import fft
from scipy.integrate import quad, solve_ivp
from scipy.interpolate import interp1d
from scipy.integrate import IntegrationWarning
from scipy.signal.windows import hann, tukey

# scipy.quad emits IntegrationWarning when its adaptive algorithm cannot
# reach the requested tolerance — usually harmless roundoff on highly
# oscillatory integrands, but occasionally a real sign of non-convergence.
#
# We do NOT silence it globally. Default behaviour: show the warning once
# per unique (message, location) pair (standard Python 'default').
# Set env var BOLTZ_QUIET_WARNINGS=1 to suppress (legacy pre-1.1 behaviour).
if os.environ.get("BOLTZ_QUIET_WARNINGS", "").strip() not in ("", "0", "false", "False"):
    warnings.filterwarnings("ignore", category=IntegrationWarning)

# NumPy 2.0+ renamed trapz → trapezoid
try:
    _trapz = np.trapezoid
except AttributeError:
    _trapz = np.trapz


# ──────────────────────────────────────────────────────────────────────────────
#  FFT-based bath correlation C(τ) = g² ∫₀^∞ J(ω) exp(-i(ω-ω₀)τ) dω
# ──────────────────────────────────────────────────────────────────────────────

def _sample_J_on_grid(J, omega):
    """Evaluate J on a numpy grid, tolerating scalar-only callables."""
    try:
        vals = J(omega)
        if not isinstance(vals, np.ndarray):
            raise TypeError
    except (TypeError, ValueError):
        vals = np.array([J(float(w)) for w in omega])
    vals = np.where(np.isfinite(vals), vals, 0.0)
    return np.maximum(vals, 0.0)  # physical: J ≥ 0


def _auto_omega_max(J, omega0, tau_max, floor_ratio=1e-6):
    """Auto-detect a sensible ω_max from J's support; enforce Nyquist on τ."""
    w_probe = np.linspace(0.0, max(100.0, 10.0 * abs(omega0)), 2000)
    J_probe = _sample_J_on_grid(J, w_probe)
    J_max = float(np.max(J_probe))
    if J_max > 0:
        above = np.where(J_probe > floor_ratio * J_max)[0]
        omega_max = float(w_probe[above[-1]]) * 1.2 if len(above) else 10.0 * abs(omega0)
    else:
        omega_max = 10.0 * abs(omega0)
    return max(omega_max, 2.0 * abs(omega0))


def _compute_bath_correlation_fft(
    J,
    *,
    g: float = 1.0,
    omega0: float = 1.0,
    tau_grid=None,
    n_freq: int = 2**14,
    omega_max: float | None = None,
    window: str = "none",
    window_alpha: float = 0.05,
    pad_factor: int = 2,
):
    """
    Compute bath correlation C(τ) = g² ∫₀^∞ J(ω) exp(-i(ω-ω₀)τ) dω via FFT.

    Replaces the O(N_τ) scipy.quad loop in the scalar implementation.
    Typical speed-up 50–500× for dense τ-grids; numerically more stable for
    oscillatory integrands (large τ) where adaptive quadrature fails to
    converge.

    Parameters
    ----------
    J : callable(ω) → float  (scalar or vectorised)
        Spectral density.
    g, omega0 : float
        Coupling constant and emitter frequency.
    tau_grid : array_like or None
        Time points at which to return C(τ). If None, the internal FFT
        τ-grid is returned.
    n_freq : int
        Number of uniform ω samples on [0, omega_max]. Default 2^14 = 16384.
    omega_max : float or None
        Upper frequency cutoff. Auto-detected from J's support if None.
    window : {"none", "tukey", "hann"}
        Window applied before FFT to suppress spectral leakage.
        ``"none"`` (default) is appropriate when ω_max is auto-selected
        (J already negligible at cutoff → truncation error O(1e-6)).
        ``"tukey"`` or ``"hann"`` recommended only for J with sharp
        features (band_edge, photonic crystal with abrupt gap) where a
        user-chosen ω_max may cut into meaningful signal.
    window_alpha : float
        Tukey taper fraction [0, 1]. Note: standard Tukey tapers BOTH
        ends, which can attenuate the signal at low ω if the density
        peak sits in the taper region. Only used if window == "tukey".
    pad_factor : int
        Zero-padding multiplier on the FFT length (improves τ-grid density).

    Returns
    -------
    (C_real, C_imag) : ndarray, ndarray
        Real and imaginary parts of C(τ) on ``tau_grid``.

    Notes
    -----
    For Lorentzian J(ω) = (γ/2π) Δ² / ((ω-ωc)² + Δ²) with ωc ≫ Δ (so the
    negative-frequency contribution is negligible), the analytical result
    is ``C(τ) = g² · γΔ/2 · exp(-Δ|τ|) · exp(-i(ωc-ω₀)τ)``. This identity
    is checked in the test suite.
    """
    tau_max = float(tau_grid[-1]) if tau_grid is not None and len(tau_grid) > 0 else 50.0

    # ── 1. ω_max (auto or user) ──
    if omega_max is None:
        omega_max = _auto_omega_max(J, omega0, tau_max)

    # ── 2. Ensure Nyquist bandwidth to resolve τ up to tau_max ──
    #    Δτ_fft = 2π / (N_total · Δω); we need Δτ_fft ≲ dt_user → enforce N ≳ ω_max·τ_max/π
    required_n = int(np.ceil(omega_max * tau_max / np.pi)) + 1
    if required_n > n_freq:
        n_freq = int(2 ** np.ceil(np.log2(required_n)))

    # ── 3. Uniform ω grid & sample J ──
    domega = omega_max / n_freq
    omega = np.arange(n_freq) * domega
    J_vals = _sample_J_on_grid(J, omega)

    # ── 4. Window to suppress truncation ringing ──
    if window == "tukey":
        win = tukey(n_freq, alpha=window_alpha)
    elif window == "hann":
        win = hann(n_freq)
    elif window == "none":
        win = np.ones(n_freq)
    else:
        raise ValueError(f"Unknown window: {window!r}")
    J_windowed = J_vals * win

    # ── 5. Zero-pad & FFT ──
    N = n_freq * max(1, int(pad_factor))
    J_padded = np.zeros(N)
    J_padded[:n_freq] = J_windowed
    C_raw = fft(J_padded)

    # ── 6. Discretisation: τ_m = 2π m / (N·Δω); scale by Δω for the Riemann sum;
    #       phase factor exp(+iω₀τ) moves the reference to ω₀ (emitter frame). ──
    dtau_fft = 2.0 * np.pi / (N * domega)
    tau_fft = np.arange(N) * dtau_fft
    C_tau = g**2 * domega * C_raw * np.exp(1j * omega0 * tau_fft)

    # ── 7. Interpolate onto user's τ-grid ──
    if tau_grid is None:
        return tau_fft, np.ascontiguousarray(C_tau.real), np.ascontiguousarray(C_tau.imag)

    tau_grid = np.asarray(tau_grid)
    # interp1d cubic if we have enough points, else linear
    kind = "cubic" if len(tau_fft) >= 4 else "linear"
    C_re = interp1d(tau_fft, C_tau.real, kind=kind,
                    fill_value=0.0, bounds_error=False)(tau_grid)
    C_im = interp1d(tau_fft, C_tau.imag, kind=kind,
                    fill_value=0.0, bounds_error=False)(tau_grid)
    return np.asarray(C_re), np.asarray(C_im)


# ──────────────────────────────────────────────────────────────────────────────
#  Backend dispatcher
# ──────────────────────────────────────────────────────────────────────────────

_VALID_BACKENDS = frozenset({"auto", "fft", "quad", "prony", "nufft"})


def _resolve_backend(backend: str, J) -> str:
    """Resolve 'auto' → concrete backend. Currently: always 'fft'.

    Future auto-selection can inspect J to detect singularities
    (band_edge → nufft), low-order exponential structure
    (Lorentzian-like → prony), etc.
    """
    if backend not in _VALID_BACKENDS:
        raise ValueError(
            f"Unknown backend {backend!r}. Valid: {sorted(_VALID_BACKENDS)}."
        )
    if backend != "auto":
        return backend
    # Phase A auto: fft by default. Phase B will extend to prony detection.
    return "fft"


def _compute_bath_correlation_quad(
    J, *, g: float, omega0: float, tau_grid, limit: int = 200,
):
    """Legacy adaptive-quadrature bath correlation.

    Kept for reference/verification. Slow (O(N_τ)·large prefactor) and
    known to fail convergence on oscillatory integrands for large τ.
    """
    # Probe J support
    w_test = np.linspace(0, max(100.0, 10.0 * abs(omega0)), 1000)
    J_test = _sample_J_on_grid(J, w_test)
    J_max = float(np.max(J_test))
    if J_max > 0:
        mask = J_test > 1e-10 * J_max
        w_max = float(w_test[mask][-1]) if np.any(mask) else 10.0 * abs(omega0)
        w_min = max(0.0, float(w_test[mask][0])) if np.any(mask) else 0.0
    else:
        w_max = 10.0 * abs(omega0)
        w_min = 0.0

    tau_grid = np.asarray(tau_grid)
    C_real = np.zeros(len(tau_grid))
    C_imag = np.zeros(len(tau_grid))
    for idx, tau in enumerate(tau_grid):
        re_part, _ = quad(
            lambda w: g**2 * J(w) * np.cos((w - omega0) * tau),
            w_min, w_max, limit=limit,
        )
        im_part, _ = quad(
            lambda w: -g**2 * J(w) * np.sin((w - omega0) * tau),
            w_min, w_max, limit=limit,
        )
        C_real[idx] = re_part
        C_imag[idx] = im_part
    return C_real, C_imag


def _build_energy_and_correlation_callables(
    tau_grid, C_real, C_imag, C_abs2, t_max: float, dt: float,
):
    """Build the scalar e_func, vectorised e_lag_func, and C_func callables
    from tabulated (τ, C_real, C_imag, |C|²) arrays.

    Returns
    -------
    (e_func, e_lag_func, C_func)
        - e_func(t, s)     : scalar, kept for API compatibility
        - e_lag_func(lag)  : vectorised, used by the fast precompute path
        - C_func(tau)      : complex bath correlation as a callable
    """
    E_cumul = np.zeros(len(tau_grid))
    for idx in range(1, len(tau_grid)):
        E_cumul[idx] = E_cumul[idx-1] + C_abs2[idx-1] * dt
    E_interp = interp1d(
        tau_grid, E_cumul,
        fill_value=(0.0, float(E_cumul[-1])), bounds_error=False,
    )

    def e_func(t, s):
        lag = t - s
        if lag <= 0:
            return 0.0
        return float(E_interp(min(lag, t_max)))

    def e_lag_func(lag):
        lag_arr = np.asarray(lag, dtype=float)
        clipped = np.clip(lag_arr, 0.0, t_max)
        out = np.asarray(E_interp(clipped), dtype=float)
        return np.where(lag_arr <= 0.0, 0.0, out)

    C_r_interp = interp1d(tau_grid, C_real, fill_value=0.0, bounds_error=False)
    C_i_interp = interp1d(tau_grid, C_imag, fill_value=0.0, bounds_error=False)

    def C_func(tau):
        return complex(C_r_interp(tau), C_i_interp(tau))

    return e_func, e_lag_func, C_func


class MemoryKernel:
    """
    Non-Markovian memory kernel K*(t,s) derived from MaxEnt variational principle.

    K*(t,s) = (1/Z(t)) exp(-e(t,s) / T_eff)

    where e(t,s) = ∫_s^t |C(τ-s)|² dτ  (accumulated correlation energy)
    and   C(τ)  = ∫ J(ω) exp(-i(ω-ω₀)τ) dω  (bath correlation function)
    """

    # Class-level attribute so hasattr / getattr work even before __init__ sets it
    _prony = None  # Optional[PronyResult]; set by from_spectral_density(backend='prony')

    def __init__(self, e_func, T_eff, t_max=100.0, dt=0.1, omega0=1.0, g=1.0,
                 gamma_markov=None, C_func=None, J_func=None,
                 _e_lag_func=None):
        """
        Parameters
        ----------
        e_func : callable(t, s) → float
            Accumulated energy density.
        T_eff : float
            Effective temperature of the environment.
        t_max : float
            Maximum simulation time.
        dt : float
            Time step for discretization.
        omega0 : float
            Emitter transition frequency.
        g : float
            Coupling constant.
        gamma_markov : float or None
            Markovian decay rate (Fermi golden rule). Computed if None.
        C_func : callable or None
            Bath correlation function C(τ).
        J_func : callable or None
            Spectral density J(ω).
        _e_lag_func : callable(lag) → array  (internal, optional)
            Vectorised evaluation of the accumulated energy as a function
            of lag τ = t - s ≥ 0. When provided, the kernel precompute
            uses a fully vectorised O(N²) path (no Python loop over j).
            Automatically set by from_spectral_density and
            from_bath_correlation. Falls back to the scalar e_func when
            absent (user-supplied custom e_func).
        """
        self.e_func = e_func
        self.T_eff = T_eff
        self.t_max = t_max
        self.dt = dt
        self.omega0 = omega0
        self.g = g
        self.C_func = C_func
        self.J_func = J_func
        self._e_lag_func = _e_lag_func

        # Precompute time grid
        self.times = np.arange(0, t_max + dt, dt)
        self.n_times = len(self.times)

        # Precompute kernel on grid
        self._K_grid = np.zeros((self.n_times, self.n_times))
        self._Z = np.zeros(self.n_times)
        self._precompute_kernel()

        # Markovian rate
        if gamma_markov is not None:
            self.gamma_markov = gamma_markov
        else:
            self.gamma_markov = self._compute_markov_rate()

    def _precompute_kernel(self):
        """Dispatch: vectorised path when a lag-aware energy function is
        available (built-in constructors), scalar fallback otherwise."""
        if self._e_lag_func is not None:
            self._precompute_kernel_vectorised()
        else:
            self._precompute_kernel_scalar()

    def _precompute_kernel_vectorised(self):
        """O(N²) vectorised precompute using the lag-only structure of e."""
        n = self.n_times
        T_safe = max(self.T_eff, 1e-30)

        # E at each possible lag (lag = times[k], k = 0..n-1)
        lag_values = self.times
        E_at_lag = np.asarray(self._e_lag_func(lag_values), dtype=float)
        unnorm_at_lag = np.exp(-E_at_lag / T_safe)

        # Build unnorm[i, j] = unnorm_at_lag[i - j] for j < i, else 0
        # via integer index array (single vectorised assignment)
        i_idx, j_idx = np.indices((n, n))
        lag_idx = i_idx - j_idx
        mask = lag_idx > 0
        unnorm = np.zeros((n, n))
        unnorm[mask] = unnorm_at_lag[lag_idx[mask]]

        # Row-wise normalisation Z[i] = ∫ unnorm[i, 0..i-1] ds
        # (small loop kept for clarity; cost is O(N) on trapz, not O(N²))
        for i in range(1, n):
            if i > 1:
                Z_i = _trapz(unnorm[i, :i], self.times[:i])
            else:
                Z_i = unnorm[i, 0] * self.dt
            self._Z[i] = max(float(Z_i), 1e-30)

        # Broadcasted normalisation (O(N²) assignment but C-level)
        Z_col = self._Z.copy()
        Z_col[Z_col == 0] = 1.0  # avoid div-by-zero for i=0 row (all zero)
        self._K_grid = unnorm / Z_col[:, None]
        self._K_grid[~mask] = 0.0  # enforce lower-triangular support

    def _precompute_kernel_scalar(self):
        """Scalar fallback for user-supplied custom e_func (non-lag or opaque)."""
        for i in range(1, self.n_times):
            t = self.times[i]
            unnorm = np.zeros(i)
            for j in range(i):
                s = self.times[j]
                e_val = self.e_func(t, s)
                unnorm[j] = np.exp(-e_val / max(self.T_eff, 1e-30))

            Z = _trapz(unnorm, self.times[:i]) if i > 1 else unnorm[0] * self.dt
            self._Z[i] = max(Z, 1e-30)

            for j in range(i):
                self._K_grid[i, j] = unnorm[j] / self._Z[i]

    def _compute_markov_rate(self):
        """Compute Fermi golden rule rate: γ = 2π g² J(ω₀)."""
        if self.J_func is not None:
            return 2 * np.pi * self.g**2 * self.J_func(self.omega0)
        return 0.1  # fallback

    def evaluate(self, t, s):
        """Evaluate K*(t, s) at arbitrary times."""
        if s >= t or s < 0:
            return 0.0
        e_val = self.e_func(t, s)
        Z, _ = quad(lambda sp: np.exp(-self.e_func(t, sp) / max(self.T_eff, 1e-30)),
                     0, t, limit=100)
        if Z < 1e-30:
            return 0.0
        return np.exp(-e_val / max(self.T_eff, 1e-30)) / Z

    def solve(self, rho0, tspan=None, method="RK45", rtol=1e-6):
        """
        Solve the non-Markovian master equation.

        dρ/dt = -i[H, ρ(t)] + ∫₀ᵗ K(t,s) D[ρ(s)] ds

        For a two-level system, we track the Bloch vector (x, y, z)
        where ρ = (I + x σ_x + y σ_y + z σ_z) / 2.

        Parameters
        ----------
        rho0 : array (2,2) or (3,) Bloch vector
            Initial state. If (2,2), converted to Bloch vector.
        tspan : array or None
            Time points. If None, uses self.times.

        Returns
        -------
        Result with .t, .rho (Bloch vectors), .populations, .coherences
        """
        if tspan is None:
            tspan = self.times

        # ── Fast path: pseudomode solver when a Prony decomposition is attached.
        #    Built by from_spectral_density(backend='prony'). O(N·K) instead of
        #    O(N²) for the integro-differential loop below.
        if self._prony is not None:
            from .pseudomode import solve_pseudomode
            pm = solve_pseudomode(
                self._prony, rho0, tspan,
                omega0=self.omega0, g=self.g,
                rtol=rtol, atol=1e-9,
            )
            return Result(pm.t, pm.bloch, self)

        # Convert rho0 to Bloch vector
        if hasattr(rho0, 'shape') and rho0.shape == (2, 2):
            x0 = 2 * np.real(rho0[0, 1])
            y0 = 2 * np.imag(rho0[1, 0])
            z0 = np.real(rho0[0, 0] - rho0[1, 1])
            bloch0 = np.array([x0, y0, z0])
        else:
            bloch0 = np.asarray(rho0, dtype=float)

        # Solve via discretized integro-differential equation
        n = len(tspan)
        dt = tspan[1] - tspan[0] if n > 1 else self.dt
        bloch = np.zeros((n, 3))
        bloch[0] = bloch0

        for i in range(1, n):
            t = tspan[i]

            integral_x = 0.0
            integral_y = 0.0
            integral_z_decay = 0.0
            integral_z_pump = 0.0

            for j in range(i):
                s = tspan[j]
                ti_idx = min(int(t / self.dt), self.n_times - 1)
                sj_idx = min(int(s / self.dt), self.n_times - 1)
                if ti_idx < self.n_times and sj_idx < ti_idx:
                    K_val = self._K_grid[ti_idx, sj_idx]
                else:
                    K_val = self.evaluate(t, s)

                integral_x += K_val * bloch[j, 0] * dt
                integral_y += K_val * bloch[j, 1] * dt
                integral_z_decay += K_val * bloch[j, 2] * dt
                integral_z_pump += K_val * dt

            gamma = self.gamma_markov
            bloch[i, 0] = bloch[i-1, 0] - 0.5 * gamma * integral_x * dt
            bloch[i, 1] = bloch[i-1, 1] - 0.5 * gamma * integral_y * dt
            bloch[i, 2] = bloch[i-1, 2] - gamma * (integral_z_decay + integral_z_pump) * dt

            # Clamp to Bloch sphere
            norm = np.sqrt(bloch[i, 0]**2 + bloch[i, 1]**2 + bloch[i, 2]**2)
            if norm > 1.0:
                bloch[i] /= norm

        return Result(tspan, bloch, self)

    @classmethod
    def from_spectral_density(
        cls, J, g=1.0, T=0.05, omega0=1.0, t_max=100.0, dt=0.1,
        *, backend: str = "auto", **backend_kwargs,
    ):
        """
        Construct a MemoryKernel from a spectral density J(ω).

        Parameters
        ----------
        J : callable(omega) → float
            Spectral density of the photonic environment. Scalar or
            vectorised; scalar-only callables are wrapped automatically.
        g : float
            System-environment coupling constant.
        T : float
            Effective temperature (energy units, ℏ=k_B=1).
        omega0 : float
            Emitter transition frequency.
        t_max : float
            Maximum simulation time.
        dt : float
            Time step.
        backend : {"auto", "quad", "fft"}
            Method used to evaluate the bath correlation
            C(τ) = g² ∫₀^∞ J(ω) exp(-i(ω-ω₀)τ) dω.

              - ``"auto"``  (default) picks the best backend for the
                problem.  Currently delegates to ``"fft"``.
              - ``"fft"``   uniform FFT after resampling J on a regular
                ω-grid. Fast (O(N log N)), stable at large τ, sensitive
                to truncation ringing for J with sharp features (mitigated
                by a Tukey window). Recommended default.
              - ``"quad"``  scalar adaptive integration (legacy scipy.quad
                path). Most robust for smooth J on bounded support; slow
                (O(N_τ) large prefactor); known to fail convergence on
                oscillatory integrands at large τ. Kept for verification
                and comparison.
        **backend_kwargs
            Forwarded to the selected backend:
              - fft:  ``n_freq``, ``omega_max``, ``window``,
                      ``window_alpha``, ``pad_factor``
              - quad: ``limit`` (default 200)

        Returns
        -------
        MemoryKernel instance.
        """
        tau_grid = np.arange(0, t_max + dt, dt)

        backend = _resolve_backend(backend, J)
        if backend == "fft":
            C_real, C_imag = _compute_bath_correlation_fft(
                J, g=g, omega0=omega0, tau_grid=tau_grid, **backend_kwargs,
            )
        elif backend == "quad":
            C_real, C_imag = _compute_bath_correlation_quad(
                J, g=g, omega0=omega0, tau_grid=tau_grid, **backend_kwargs,
            )
        elif backend == "prony":
            # Phase B: FFT-compute C(τ) → Prony-decompose → attach for pseudomode .solve()
            # The prony_kwargs go to prony_decompose; remaining go to FFT.
            prony_kwargs = {}
            for key in ("n_exp", "max_n_exp", "variance_threshold",
                        "use_maxent_selector", "entropy_ratio_threshold",
                        "enforce_stable"):
                if key in backend_kwargs:
                    prony_kwargs[key] = backend_kwargs.pop(key)
            C_real, C_imag = _compute_bath_correlation_fft(
                J, g=g, omega0=omega0, tau_grid=tau_grid, **backend_kwargs,
            )
            # Import lazily to avoid cycle at module load
            from .prony import prony_decompose, maxent_select_order
            C_complex = C_real + 1j * C_imag

            use_maxent = prony_kwargs.pop("use_maxent_selector", False)
            entropy_thr = prony_kwargs.pop("entropy_ratio_threshold", 0.95)
            if use_maxent and "n_exp" not in prony_kwargs:
                # Pre-compute SVD to feed MaxEnt selector, then fix n_exp
                # (Slight redundancy — Prony re-does SVD internally.
                # Accepted cost: MaxEnt selector is a novel contribution
                # worth exposing as an explicit knob.)
                import numpy as _np_tmp
                n = len(C_complex)
                L = n // 2
                H = _np_tmp.asarray(
                    [[C_complex[i + j] for j in range(n - L)] for i in range(L + 1)],
                    dtype=complex,
                )
                _, sv, _ = _np_tmp.linalg.svd(H, full_matrices=False)
                prony_kwargs["n_exp"] = maxent_select_order(
                    sv,
                    max_n_exp=prony_kwargs.get("max_n_exp", 16),
                    entropy_ratio_threshold=entropy_thr,
                )
            prony_result = prony_decompose(tau_grid, C_complex, **prony_kwargs)
        elif backend == "nufft":
            raise NotImplementedError(
                "NUFFT backend is scheduled for Phase C. "
                "Use backend='fft' (default) for most J, or 'quad' for "
                "reference validation."
            )
        else:
            raise ValueError(
                f"Unknown backend {backend!r}. "
                f"Valid choices: {sorted(_VALID_BACKENDS)}."
            )

        C_abs2 = C_real**2 + C_imag**2

        e_func, e_lag_func, C_func = _build_energy_and_correlation_callables(
            tau_grid, C_real, C_imag, C_abs2, t_max, dt,
        )

        instance = cls(
            e_func=e_func, T_eff=T, t_max=t_max, dt=dt,
            omega0=omega0, g=g, C_func=C_func, J_func=J,
            _e_lag_func=e_lag_func,
        )
        # Attach Prony decomposition if the prony backend was used.
        # .solve() will then dispatch to the O(N·K) pseudomode path
        # instead of the O(N²) integro-differential loop.
        if backend == "prony":
            instance._prony = prony_result  # type: ignore[attr-defined]
        return instance

    @classmethod
    def from_bath_correlation(cls, C, T=0.05, t_max=100.0, dt=0.1, omega0=1.0, g=1.0):
        """
        Construct a MemoryKernel from a bath correlation function C(τ).

        Uses the vectorised precompute fast-path (e is a pure function of
        the lag τ = t - s).
        """
        tau_grid = np.arange(0, t_max + dt, dt)
        C_vals = np.array([C(tau) for tau in tau_grid], dtype=complex)
        C_real = C_vals.real
        C_imag = C_vals.imag
        C_abs2 = C_real**2 + C_imag**2

        e_func, e_lag_func, C_func_built = _build_energy_and_correlation_callables(
            tau_grid, C_real, C_imag, C_abs2, t_max, dt,
        )
        # Preserve the user-provided C callable rather than our interpolant
        return cls(
            e_func=e_func, T_eff=T, t_max=t_max, dt=dt,
            omega0=omega0, g=g, C_func=C, _e_lag_func=e_lag_func,
        )

    def non_markovianity(self):
        """
        Compute the non-Markovianity parameter P = g × τ_c
        where τ_c = ∫ τ K*(τ) dτ is the memory correlation time.
        """
        t_idx = self.n_times // 2
        if t_idx < 2:
            return 0.0

        K_slice = self._K_grid[t_idx, :t_idx]
        t_slice = self.times[:t_idx]

        if len(K_slice) < 2 or np.sum(K_slice) < 1e-30:
            return 0.0

        lags = self.times[t_idx] - t_slice
        tau_c = _trapz(lags * K_slice, t_slice) / max(_trapz(K_slice, t_slice), 1e-30)

        return self.g * tau_c

    def memory_spread(self):
        """Compute σ_K — the std dev of the kernel as a distribution over lag times."""
        t_idx = self.n_times // 2
        if t_idx < 2:
            return 0.0

        K_slice = self._K_grid[t_idx, :t_idx]
        t_slice = self.times[:t_idx]
        lags = self.times[t_idx] - t_slice
        norm = _trapz(K_slice, t_slice)
        if norm < 1e-30:
            return 0.0

        mean_lag = _trapz(lags * K_slice, t_slice) / norm
        var_lag = _trapz((lags - mean_lag)**2 * K_slice, t_slice) / norm
        return np.sqrt(max(var_lag, 0))

    def kernel_at(self, t):
        """Return K*(t, s) as arrays (s_values, K_values) for plotting."""
        t_idx = min(int(t / self.dt), self.n_times - 1)
        if t_idx < 1:
            return np.array([0]), np.array([0])
        s_vals = self.times[:t_idx]
        K_vals = self._K_grid[t_idx, :t_idx]
        return s_vals, K_vals


class Result:
    """Container for solver output."""

    def __init__(self, t, bloch, kernel):
        self.t = np.asarray(t)
        self.bloch = np.asarray(bloch)
        self.kernel = kernel

    @property
    def x(self):
        return self.bloch[:, 0]

    @property
    def y(self):
        return self.bloch[:, 1]

    @property
    def z(self):
        return self.bloch[:, 2]

    @property
    def populations(self):
        """Excited state population P_e = (1+z)/2."""
        return (1 + self.z) / 2

    @property
    def coherences(self):
        """Off-diagonal |ρ₀₁| = sqrt(x² + y²)/2."""
        return np.sqrt(self.x**2 + self.y**2) / 2

    def trace_distance_from(self, other):
        """Trace distance D(ρ_self, ρ_other) at each time step."""
        dx = self.x - other.x
        dy = self.y - other.y
        dz = self.z - other.z
        return 0.5 * np.sqrt(dx**2 + dy**2 + dz**2)
