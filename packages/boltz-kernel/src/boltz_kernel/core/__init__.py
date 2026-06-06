"""
BoltZ-Kernel core computational engine.

Public API:
    MemoryKernel            — Boltzmann (MaxEnt) memory kernel K*(t, s)
    Result                  — Time-series container (Bloch vector + metadata)
    LindbladSolver          — Markov-limit analytical baseline
    compare()               — One-call NM-vs-Lindblad comparison
    ComparisonResult        — Container with trace distance, regime, plotting
    SpectralDensities       — Library of common photonic J(ω)

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-BoltZ-Commercial
"""

from .compare import ComparisonResult, SpectralDensities, compare
from .kernel import MemoryKernel, Result
from .lindblad import LindbladSolver

__all__ = [
    "MemoryKernel",
    "Result",
    "LindbladSolver",
    "compare",
    "ComparisonResult",
    "SpectralDensities",
]
