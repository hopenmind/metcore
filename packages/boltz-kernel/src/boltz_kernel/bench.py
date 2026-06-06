"""
Reproducible reference benchmarks — proves the solver against known exact results.

Each benchmark runs the comparison and checks the numerical output against
an analytical reference, reporting the discrepancy. Used in the README,
in publications, and by reviewers.

Cases (pending full implementation):
  - jaynes-cummings : damped emitter in a single-mode cavity (Breuer–Piilo)
  - pure-dephasing  : exact decoherence function via J(ω) → γ(t)
  - ohmic-markov    : Ohmic bath in the van Hove limit → exponential decay

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-BoltZ-Commercial
"""

from __future__ import annotations

import sys
from pathlib import Path


KNOWN_CASES = ("jaynes-cummings", "pure-dephasing", "ohmic-markov")


def run_bench(*, case: str, output_dir: Path) -> int:
    """Return exit code. Pending full implementation (Round 2)."""
    if case not in KNOWN_CASES:
        sys.stderr.write(
            f"Unknown benchmark case: {case!r}\n"
            f"Known cases: {', '.join(KNOWN_CASES)}\n"
        )
        return 2
    sys.stderr.write(
        f"Benchmark case {case!r} is pending full implementation (Round 2).\n"
        f"Output would go to: {output_dir}\n"
        "Analytical references have been selected; implementation follows\n"
        "the general schema used by `boltz-kernel run`.\n"
    )
    return 2
