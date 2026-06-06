"""
BoltZ-Kernel — Non-Markovian quantum dynamics solver.

Boltzmann memory kernel (MaxEnt-Jaynes derivation) for open quantum systems
beyond the Lindblad Markov approximation.

Three equations of the formalism:

  1. Generalised master equation:
     dρ/dt = -i[H, ρ] + ∫₀ᵗ K(t, s) · D[ρ(s)] ds

  2. Boltzmann memory kernel (MaxEnt-derived):
     K*(t, s) = exp(-e(t, s) / T_eff) / Z(t)
     where e(t, s) = ∫ₛᵗ |C(τ - s)|² dτ

  3. Bath correlation from spectral density:
     C(τ) = g² · ∫₀∞ J(ω) · exp(-i (ω - ω₀) τ) dω

Dual-licensed:
  - Academic / non-commercial: Apache-2.0 (cite DOI 10.5281/zenodo.19648837)
  - Commercial use:             Proprietary (contact@hopenmind.com)

Author:  DESVAUX G.J.Y.  (ORCID 0009-0008-9813-4627)
DOI:     10.5281/zenodo.19648837
Repo:    https://github.com/hopenmind/hopenmind-suite
"""

import numpy as np

# NumPy 2.0 compatibility (removed np.trapz)
if not hasattr(np, "trapz"):
    np.trapz = np.trapezoid

from .core import (
    ComparisonResult,
    LindbladSolver,
    MemoryKernel,
    Result,
    SpectralDensities,
    compare,
)

__version__ = "1.1.0"
__author__ = "DESVAUX G.J.Y."
__license__ = "Apache-2.0 OR LicenseRef-BoltZ-Commercial"
__doi__ = "10.5281/zenodo.19648837"
__contact__ = "contact@hopenmind.com"

__all__ = [
    "MemoryKernel",
    "Result",
    "LindbladSolver",
    "compare",
    "ComparisonResult",
    "SpectralDensities",
    "__version__",
]
