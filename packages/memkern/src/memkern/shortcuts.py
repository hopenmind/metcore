"""Analytic shortcuts: one-stroke closed-form answers.

Each function here replaces a numerical campaign (parameter sweeps, full
integro-differential integration, behavioral experiments) by an explicit
formula from the MET corpus. Inputs are plain Prony data or scalars; outputs
are dicts with the number, the formula used, and what the normal route costs.

Sources: paper1b (exterior Lindbladian), paper2 Eq. 6 (memory-modified
Kuramoto threshold), paper3a Prop. 2 (resonance line shape) and Cor. 1
(reaction-time scaling).

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
Author: DESVAUX G.J.Y. - Hope 'n Mind SASU - Research
"""
from __future__ import annotations

import numpy as np


def exterior_rate(alphas, betas) -> dict:
    """Asymptotic (exterior) Lindblad rate from Prony data, in one stroke.

    gamma_M = Re K_hat(0) = Re sum_k alpha_k / beta_k.
    Replaces: integrating the full Nakajima-Zwanzig dynamics to t -> infinity
    and extracting the time-local generator (typically minutes of ODE work).
    """
    a = np.asarray(alphas, dtype=complex).ravel()
    b = np.asarray(betas, dtype=complex).ravel()
    if a.size != b.size or a.size == 0:
        raise ValueError("alphas and betas must be same nonzero length")
    if np.any(np.real(b) <= 0):
        raise ValueError("all Re(beta_k) must be > 0 (decaying modes)")
    khat0 = complex(np.sum(a / b))
    gamma_m = float(np.real(khat0))
    return {
        "khat0": {"re": khat0.real, "im": khat0.imag},
        "gamma_markov": gamma_m,
        "gksl_admissible": bool(gamma_m >= 0.0),
        "formula": "gamma_M = Re sum_k alpha_k/beta_k",
        "replaces": "full NZ integration to t->inf + generator extraction",
        "verdict": ("asymptotic Markovian envelope exists (gamma_M >= 0)"
                    if gamma_m >= 0 else
                    "boundary GKSL fails: no admissible Markovian envelope"),
    }


def kuramoto_kc(alphas, betas, gamma_g: float, omega0: float = 0.0) -> dict:
    """Memory-modified synchronization threshold (paper2, Eq. 6), one stroke.

    For a Lorentzian frequency distribution of half-width gamma_g centered at
    omega0, the memoryless Kuramoto threshold is K_c0 = 2*gamma_g. A memory
    kernel M(tau) = sum_k alpha_k exp(-beta_k tau) rescales it:
        K_c(M) = K_c0 / M_hat(0),   M_hat(0) = sum_k alpha_k/beta_k.
    Replaces: sweeping K over a grid, integrating the retarded Kuramoto model
    at each K, and locating the transition (typically 10+ minutes / system).
    """
    if gamma_g <= 0:
        raise ValueError("gamma_g must be > 0")
    a = np.asarray(alphas, dtype=complex).ravel()
    b = np.asarray(betas, dtype=complex).ravel()
    if a.size != b.size or a.size == 0:
        raise ValueError("alphas and betas must be same nonzero length")
    if np.any(np.real(b) <= 0):
        raise ValueError("all Re(beta_k) must be > 0")
    mhat0 = float(np.real(np.sum(a / b)))
    kc0 = 2.0 * float(gamma_g)
    if mhat0 <= 0:
        return {"M_hat0": mhat0, "K_c_memoryless": kc0, "K_c": None,
                "verdict": "M_hat(0) <= 0: no synchronized phase at any K "
                           "(memory destroys synchronization)",
                "formula": "K_c = 2*gamma_g / M_hat(0)"}
    kc = kc0 / mhat0
    return {
        "M_hat0": mhat0,
        "K_c_memoryless": kc0,
        "K_c": kc,
        "ratio": kc / kc0,
        "formula": "K_c = 2*gamma_g / M_hat(0), M_hat(0) = sum alpha_k/beta_k",
        "replaces": "K-sweep of the retarded Kuramoto model + transition fit",
        "verdict": (f"memory {'lowers' if kc < kc0 else 'raises'} the "
                    f"synchronization threshold by x{kc/kc0:.3g}"),
    }


def rf_resonance_shift(A: float, omega_p: float, omega0: float,
                       gamma0: float, m_base0: float) -> dict:
    """Relative shift of the synchronization threshold under a periodic
    perturbation (paper3a, Prop. 2): a Lorentzian line shape, one stroke.

        dKc/Kc = [A/w_p^2] / [M_base(0) - A/w_p^2]
                 * gamma0^2 / ((w_p - w0)^2 + gamma0^2)

    Replaces: re-running the full threshold sweep at every perturbation
    frequency (N_freq x full simulation).
    """
    if omega_p <= 0 or gamma0 <= 0 or m_base0 <= 0:
        raise ValueError("omega_p, gamma0 and m_base0 must be > 0")
    drive = float(A) / float(omega_p) ** 2
    denom = float(m_base0) - drive
    if denom <= 0:
        return {"shift_relative": None,
                "verdict": "perturbation overwhelms the base kernel "
                           "(A/omega_p^2 >= M_base(0)): threshold diverges",
                "formula": "dKc/Kc = (A/w_p^2)/(M0 - A/w_p^2) * L(w_p)"}
    lorentz = float(gamma0) ** 2 / ((float(omega_p) - float(omega0)) ** 2
                                    + float(gamma0) ** 2)
    shift = drive / denom * lorentz
    return {
        "shift_relative": shift,
        "lorentzian_factor": lorentz,
        "on_resonance": bool(abs(omega_p - omega0) <= gamma0),
        "formula": "dKc/Kc = (A/w_p^2)/(M0 - A/w_p^2) * g0^2/((w_p-w0)^2+g0^2)",
        "replaces": "threshold sweep re-run at every perturbation frequency",
        "verdict": f"relative threshold shift {shift:+.4g} "
                   f"({'on' if abs(omega_p-omega0)<=gamma0 else 'off'}-resonance)",
    }


def rt_scaling(tau_l: float, tau_d: float, theta: float, i0: float) -> dict:
    """Mean reaction time from kernel parameters (paper3a, Cor. 1), one stroke.

        <RT> = tau_l + tau_d * ln(theta / I0),    sigma_RT ~ tau_d.

    Replaces: a behavioral 2AFC campaign (subjects x trials) plus
    inverse-Gaussian fitting, when the question is only the scaling.
    """
    if tau_d <= 0 or theta <= 0 or i0 <= 0:
        raise ValueError("tau_d, theta and i0 must be > 0")
    if i0 >= theta:
        return {"rt_mean": float(tau_l),
                "verdict": "stimulus integral already exceeds threshold: "
                           "RT is conduction-limited (= tau_l)",
                "formula": "<RT> = tau_l + tau_d*ln(theta/I0)"}
    rt = float(tau_l) + float(tau_d) * float(np.log(theta / i0))
    return {
        "rt_mean": rt,
        "rt_sigma_scale": float(tau_d),
        "formula": "<RT> = tau_l + tau_d*ln(theta/I0); sigma_RT ~ tau_d",
        "replaces": "behavioral RT campaign + inverse-Gaussian fit",
        "verdict": f"predicted mean RT = {rt:.4g} (same unit as tau_l/tau_d)",
    }
