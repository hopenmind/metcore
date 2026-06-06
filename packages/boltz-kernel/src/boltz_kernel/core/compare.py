"""
Comparison module: Non-Markovian vs Lindblad dynamics.

Provides:
  - compare(J, g, T, omega0, rho0, ...) → ComparisonResult
  - Plotting helpers
  - Spectral density library (common photonic environments)

DOI: 10.5281/zenodo.19648837 | ORCID: 0009-0008-9813-4627
SPDX-License-Identifier: Apache-2.0 OR LicenseRef-BoltZ-Commercial
"""

import numpy as np
from .kernel import MemoryKernel
from .lindblad import LindbladSolver


class ComparisonResult:
    """Container for NM vs Markov comparison."""

    def __init__(self, nm_result, m_result, kernel):
        self.nm = nm_result
        self.markov = m_result
        self.kernel = kernel
        self.t = nm_result.t

    @property
    def trace_distance(self):
        """D(ρ_NM, ρ_M) at each time."""
        return self.nm.trace_distance_from(self.markov)

    @property
    def max_deviation(self):
        """Max trace distance over all times."""
        return np.max(self.trace_distance)

    @property
    def regime(self):
        """Classify the regime based on non-Markovianity parameter."""
        P = self.kernel.non_markovianity()
        if P < 0.1:
            return "Markovian"
        elif P < 1.0:
            return "Weakly non-Markovian"
        else:
            return "Strongly non-Markovian"

    def summary(self):
        """Return formatted summary string."""
        P = self.kernel.non_markovianity()
        sigma = self.kernel.memory_spread()
        max_d = self.max_deviation
        lines = [
            "=" * 55,
            "  Non-Markovian vs Lindblad — Comparison",
            "  Hope 'n Mind SASU - Research | DOI: 10.5281/zenodo.19648837",
            "=" * 55,
            f"  Regime:              {self.regime}",
            f"  Memory parameter P:  {P:.4f}",
            f"  Memory spread sigma_K: {sigma:.4f}",
            f"  Max trace distance:  {max_d:.4f}",
            f"  Lindblad valid:      {'Yes' if max_d < 0.01 else 'No'}",
            "=" * 55,
        ]
        return "\n".join(lines)

    def plot(self, show=True, save=None, branding=None, metadata=None, source_label=None):
        """
        Plot comparison: populations, coherences, trace distance, kernel.

        Parameters
        ----------
        branding     : BrandingConfig or None
        metadata     : dict or None   — hidden file metadata (PNG/PDF/SVG)
        source_label : str or None    — spectral density name shown top-left
        """
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
        except ImportError:
            print("matplotlib not available. Install with: pip install matplotlib")
            return

        fig, axes = plt.subplots(2, 2, figsize=(12, 9))

        if branding is not None:
            branding.apply_to_figure(fig, source_label=source_label)
        else:
            fig.suptitle(
                "Non-Markovian vs Lindblad Dynamics\n"
                "Hope 'n Mind SASU - Research — DOI: 10.5281/zenodo.19648837",
                fontsize=13, fontweight='bold'
            )
            if source_label:
                fig.text(
                    0.01, 0.895, f"J(\u03c9): {source_label}",
                    ha='left', va='top',
                    fontsize=7.5, color='#444444', style='italic'
                )

        # 1. Excited state population
        ax = axes[0, 0]
        ax.plot(self.t, self.nm.populations, 'b-', lw=2, label='Non-Markovian')
        ax.plot(self.t, self.markov.populations, 'r--', lw=2, label='Lindblad')
        ax.set_xlabel('Time')
        ax.set_ylabel('P_e(t)')
        ax.set_title('Excited State Population')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 2. Coherences
        ax = axes[0, 1]
        ax.plot(self.t, self.nm.coherences, 'b-', lw=2, label='Non-Markovian')
        ax.plot(self.t, self.markov.coherences, 'r--', lw=2, label='Lindblad')
        ax.set_xlabel('Time')
        ax.set_ylabel('|ρ₀₁(t)|')
        ax.set_title('Coherence')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 3. Trace distance
        ax = axes[1, 0]
        td = self.trace_distance
        ax.plot(self.t, td, 'k-', lw=2)
        ax.axhline(0.01, color='orange', ls='--', label='1% threshold')
        ax.fill_between(self.t, 0, td, alpha=0.2, color='purple')
        ax.set_xlabel('Time')
        ax.set_ylabel('D(ρ_NM, ρ_M)')
        ax.set_title(f'Trace Distance — Max: {self.max_deviation:.4f}')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 4. Memory kernel
        ax = axes[1, 1]
        t_mid = self.kernel.t_max / 2
        s_vals, K_vals = self.kernel.kernel_at(t_mid)
        if len(s_vals) > 1:
            lags = t_mid - s_vals
            ax.plot(lags, K_vals, 'g-', lw=2)
            ax.set_xlabel('Lag (t - s)')
            ax.set_ylabel('K*(t, s)')
            ax.set_title(f'Memory Kernel at t={t_mid:.1f}')
        else:
            ax.text(0.5, 0.5, 'Kernel too short\nto display',
                    ha='center', va='center', transform=ax.transAxes)
        ax.grid(True, alpha=0.3)

        plt.tight_layout(rect=[0, 0.03, 1, 0.93])

        if save:
            import os as _os
            import matplotlib as _mpl
            _ext = _os.path.splitext(save)[1].lower().lstrip(".")
            _save_kw = {"dpi": 150, "bbox_inches": "tight", "facecolor": "white"}
            if branding is not None:
                _meta = branding.metadata_for_format(_ext)
                if _meta is not None:
                    _save_kw["metadata"] = _meta
            elif metadata:
                _save_kw["metadata"] = metadata
            # Force Type 42 fonts for EPS so Inkscape/Illustrator don't crash
            _prev = _mpl.rcParams.get('ps.fonttype', 3)
            if _ext == "eps":
                _mpl.rcParams['ps.fonttype'] = 42
            fig.savefig(save, **_save_kw)
            if _ext == "eps":
                _mpl.rcParams['ps.fonttype'] = _prev
        if show:
            plt.show()
        plt.close(fig)
        return fig


def compare(J, g=1.0, T=0.05, omega0=1.0, rho0=None, t_max=50.0, dt=0.2,
            *, backend="auto", **backend_kwargs):
    """
    One-call comparison: Non-Markovian vs Lindblad.

    Parameters
    ----------
    J : callable(omega) → float
        Spectral density of the environment.
    g : float
        Coupling constant.
    T : float
        Effective temperature.
    omega0 : float
        Emitter frequency.
    rho0 : array or None
        Initial state. Default: |e⟩ (excited state).
    t_max : float
        Maximum time.
    dt : float
        Time step.
    backend : str
        Bath-correlation / solver backend for the NM branch.
        See ``MemoryKernel.from_spectral_density`` for options:
        ``"auto"`` (default) → ``"fft"`` ; ``"quad"`` (legacy) ;
        ``"prony"`` (FFT + pseudomode, fastest ``.solve()``) ;
        ``"nufft"`` (Phase C).
    **backend_kwargs
        Passed through to the backend (e.g. ``n_exp``, ``use_maxent_selector``
        for prony; ``n_freq``, ``window``, ``pad_factor`` for fft).

    Returns
    -------
    ComparisonResult
    """
    if rho0 is None:
        rho0 = np.array([0.0, 0.0, 1.0])  # excited state on Bloch sphere

    K = MemoryKernel.from_spectral_density(
        J, g=g, T=T, omega0=omega0, t_max=t_max, dt=dt,
        backend=backend, **backend_kwargs,
    )
    L = LindbladSolver.from_spectral_density(J, g=g, omega0=omega0)
    tspan = np.arange(0, t_max + dt, dt)
    nm_result = K.solve(rho0, tspan)
    m_result = L.solve(rho0, tspan)

    return ComparisonResult(nm_result, m_result, K)


# ================================================================
# Spectral density library — common photonic environments
# ================================================================

class SpectralDensities:
    """Library of common spectral densities for photonic systems."""

    @staticmethod
    def ohmic(eta=0.1, wc=10.0, s=1):
        """Ohmic spectral density: J(ω) = η ωˢ exp(-ω/ωc)"""
        def J(w):
            if w <= 0:
                return 0.0
            return eta * w**s * np.exp(-w / wc)
        J.__doc__ = f"Ohmic(η={eta}, ωc={wc}, s={s})"
        return J

    @staticmethod
    def lorentzian(gamma=0.1, wc=5.0, width=0.5):
        """Lorentzian (cavity): J(ω) = (γ/2π) · Δ² / ((ω-ωc)² + Δ²)"""
        def J(w):
            return (gamma / (2 * np.pi)) * width**2 / ((w - wc)**2 + width**2)
        J.__doc__ = f"Lorentzian(γ={gamma}, ωc={wc}, Δ={width})"
        return J

    @staticmethod
    def band_edge(beta=0.05, we=5.0):
        """Photonic band edge: J(ω) = β^{3/2} / √(ω - ωe) for ω > ωe"""
        def J(w):
            if w <= we:
                return 0.0
            return beta**1.5 / np.sqrt(w - we)
        J.__doc__ = f"BandEdge(β={beta}, ωe={we})"
        return J

    @staticmethod
    def photonic_crystal(beta=0.05, we=5.0, gap_width=2.0):
        """Photonic crystal with gap: J(ω) = 0 for ωe < ω < ωe + gap, band edge outside."""
        def J(w):
            if w <= we or (we < w < we + gap_width):
                return 0.0
            return beta**1.5 / np.sqrt(w - we - gap_width)
        J.__doc__ = f"PhC(β={beta}, ωe={we}, gap={gap_width})"
        return J

    @staticmethod
    def waveguide(gamma_1d=0.5, tau_rt=1.0, r=0.9, n_modes=50):
        """Waveguide QED with mirror: J(ω) = (Γ_1D/2π) / (1 + r² - 2r cos(ω τ_rt))"""
        def J(w):
            denom = 1 + r**2 - 2 * r * np.cos(w * tau_rt)
            return (gamma_1d / (2 * np.pi)) / max(denom, 1e-10)
        J.__doc__ = f"Waveguide(Γ_1D={gamma_1d}, τ_rt={tau_rt}, r={r})"
        return J
