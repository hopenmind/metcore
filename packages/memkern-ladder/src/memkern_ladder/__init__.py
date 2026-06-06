"""memkern-ladder — 3-level approximation ladder for NZ dynamics.

Level 1 — Markovian Lindblad         (analytical, O(seconds) on laptop)
Level 2 — Born-Markov + 1st-order NZ correction
Level 3 — Prony-pseudomode exact    (memkern, K-mode ODE system)

Each level solves the problem; the ladder stops at the first level
whose residual vs. level N+1 is under the target accuracy. When no
level meets the accuracy, the verdict escalates to HPC-tier tools
(``hpc-oracle``, ``bench-extrap``).

Deliberate scope: this package ships only levels 1-3. HEOM and
path-integral (higher tiers) are NOT placeholder levels here — they
are separate modules scheduled for future release and only invoked by
escalation downstream. See the project NOVELTY note in README.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

from memkern_ladder.tool import (
    MemkernLadderTool,
    memkern_ladder_tool,
    solve_level_1,
    solve_level_2,
    solve_level_3,
)

__all__ = [
    "MemkernLadderTool",
    "memkern_ladder_tool",
    "solve_level_1",
    "solve_level_2",
    "solve_level_3",
]

__version__ = "0.1.0"
__author__ = "DESVAUX G.J.Y."
__contact__ = "contact@hopenmind.com"
__license__ = "Apache-2.0 OR LicenseRef-HopenMind-Commercial"
