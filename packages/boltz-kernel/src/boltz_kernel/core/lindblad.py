"""
Standard Lindblad (Markovian) solver — analytical comparison baseline.

dρ/dt = -i[H, ρ] + γ (σ₋ ρ σ₊ - ½ {σ₊ σ₋, ρ})

Bloch-sphere form:
  dx/dt = -γ x / 2
  dy/dt = -γ y / 2
  dz/dt = -γ (z + 1)

DOI: 10.5281/zenodo.19648837 | ORCID: 0009-0008-9813-4627
SPDX-License-Identifier: Apache-2.0 OR LicenseRef-BoltZ-Commercial
"""

import numpy as np
from .kernel import Result


class LindbladSolver:
    """Markovian Lindblad solver for a two-level system."""

    def __init__(self, gamma, omega0=1.0):
        """
        Parameters
        ----------
        gamma : float
            Spontaneous emission rate (Fermi golden rule: γ = 2π g² J(ω₀)).
        omega0 : float
            Emitter transition frequency.
        """
        self.gamma = gamma
        self.omega0 = omega0

    @classmethod
    def from_spectral_density(cls, J, g=1.0, omega0=1.0):
        """Compute Markovian rate from Fermi golden rule."""
        gamma = 2 * np.pi * g**2 * J(omega0)
        return cls(gamma=gamma, omega0=omega0)

    def solve(self, rho0, tspan):
        """
        Solve Lindblad equation analytically.

        Parameters
        ----------
        rho0 : array (2,2) or (3,) Bloch vector
            Initial state.
        tspan : array
            Time points.

        Returns
        -------
        Result with .t, .bloch, .populations, .coherences
        """
        tspan = np.asarray(tspan)

        if hasattr(rho0, 'shape') and rho0.shape == (2, 2):
            x0 = 2 * np.real(rho0[0, 1])
            y0 = 2 * np.imag(rho0[1, 0])
            z0 = np.real(rho0[0, 0] - rho0[1, 1])
        else:
            rho0 = np.asarray(rho0, dtype=float)
            x0, y0, z0 = rho0[0], rho0[1], rho0[2]

        gamma = self.gamma

        bloch = np.zeros((len(tspan), 3))
        bloch[:, 0] = x0 * np.exp(-gamma * tspan / 2)
        bloch[:, 1] = y0 * np.exp(-gamma * tspan / 2)
        bloch[:, 2] = -1 + (z0 + 1) * np.exp(-gamma * tspan)

        return Result(tspan, bloch, kernel=None)
