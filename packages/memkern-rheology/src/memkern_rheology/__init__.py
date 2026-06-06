"""memkern-rheology — Maxwell-Wiechert adapter for memkern.

The generalised Maxwell (Wiechert) model of linear viscoelasticity
writes the relaxation modulus as

    G(t) = G_∞ + Σ_k G_k · exp(-t/τ_k)

which is *literally* a Prony series with a DC offset. Fitting it from
measured ``G(t)`` data is exactly what ``memkern.prony_decompose``
does; this package is a thin, well-documented adapter that uses
rheology conventions (moduli, relaxation times, storage/loss moduli
via Fourier transform of the Prony series) instead of bath-correlation
conventions.

Public surface (0.1.x):
  * ``fit_maxwell_wiechert`` — end-to-end fit from ``(t, G(t))``
  * ``MaxwellWiechertResult`` — immutable result container
  * ``evaluate_modulus`` — forward prediction G(t) from parameters
  * ``storage_loss_moduli`` — G'(ω), G''(ω) from the fitted Prony series

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

from memkern_rheology.core import (
    MaxwellWiechertResult,
    evaluate_modulus,
    fit_maxwell_wiechert,
    storage_loss_moduli,
)

__all__ = [
    "MaxwellWiechertResult",
    "evaluate_modulus",
    "fit_maxwell_wiechert",
    "storage_loss_moduli",
]

__version__ = "0.1.0"
__author__ = "DESVAUX G.J.Y."
__contact__ = "contact@hopenmind.com"
__license__ = "Apache-2.0 OR LicenseRef-HopenMind-Commercial"
