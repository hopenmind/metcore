"""memkern - the MET-Compiler of the Hope 'n Mind Scientific Suite.

Mathematical engine: given a memory kernel sampled from any domain
(bath correlation C(τ) of an open quantum system, relaxation modulus
G(t) of a viscoelastic material, impulse response of a climate model,
translation-lag kernel of a gene-regulatory circuit, ...), memkern
performs the three steps of the Markov Embedding Theorem:

    1. RATIONAL APPROXIMATION   Ĉ(s) = P(s) / Q(s)  via Matrix-Pencil
    2. PRONY DECOMPOSITION      C(τ) = Σₖ cₖ · exp(-μₖ τ) · 𝓛ₖ
    3. ORDER SELECTION          K = min order preserving 95 %
                                 singular-value-weight entropy
                                 (``maxent_select_order``, NOVEL)

The Prony output feeds domain adapters (boltz-kernel, memkern-rheology,
...) that compile the K exponential modes into a finite-dimensional
Markovian ODE in an extended state space - the MET embedding proper.
The auxiliary dimension K is thus an experimental observable of the
kernel, not a modeller's knob.

Public surface (0.1.x):
  * ``prony_decompose``    - Matrix-Pencil exponential fit
  * ``maxent_select_order`` - MaxEnt-based order selection (NOVEL)
  * ``PronyResult``        - immutable result container

Planned additions:
  * FFT-based bath/auto-correlation transforms (lift from boltz-kernel)
  * Pseudomode (TCL2-style) reduction from Prony modes
  * AAA (Adaptive Antoulas-Anderson) rational approximation backend
  * Matrix-valued kernels for multi-dissipator embeddings

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

from memkern.diagnostics import bootstrap_order, embeddability_report, hankel_singular_spectrum
from memkern.embedding import lindblad_gap, exterior_lindblad_rate
from memkern.cptp import cptp_certify
from memkern.pipeline import full_diagnosis
from memkern.adapters import quantum_kernel, neural_kernel, spectral_density
from memkern import zoo
from memkern.prony import (
    PronyResult,
    maxent_select_order,
    prony_decompose,
)

__all__ = [
    "PronyResult",
    "embeddability_report",
    "bootstrap_order",
    "hankel_singular_spectrum",
    "lindblad_gap",
    "exterior_lindblad_rate",
    "cptp_certify",
    "full_diagnosis",
    "quantum_kernel",
    "neural_kernel",
    "spectral_density",
    "zoo",
    "maxent_select_order",
    "prony_decompose",
]

__version__ = "0.1.0"
__author__ = "DESVAUX G.J.Y."
__contact__ = "contact@hopenmind.com"
__license__ = "Apache-2.0 OR LicenseRef-HopenMind-Commercial"

from memkern.shortcuts import (  # analytic one-stroke shortcuts
    exterior_rate, kuramoto_kc, rf_resonance_shift, rt_scaling)
