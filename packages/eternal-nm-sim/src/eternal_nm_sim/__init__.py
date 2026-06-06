"""eternal-nm-sim — canonical fixtures for eternal non-Markovianity.

Implements the Hall et al. 2014 Pauli channel whose Lindblad-form
decoherence rates satisfy ``γ_x + γ_y + γ_z ≥ 0`` (CPTP) while
``γ_z(t) < 0`` for all t > 0 (eternal non-Markovianity). This channel
is the canonical counter-example to "information-backflow implies
non-Markovianity": its BLP measure is zero yet the dynamics is not
CP-divisible.

The companion comparison utilities evaluate BLP (trace-distance
increase) and N_G (geometric-volume increase, from ``ng-vol``) on the
same channel, making the complementarity of the two measures explicit.

Public surface (0.1.x):
  * ``hall_channel`` — Pauli channel with γ_x=γ_y=1, γ_z=-tanh(t)
  * ``pauli_channel`` — generic γ-driven Pauli channel builder
  * ``blp_measure`` — BLP non-Markovianity from trace-distance revivals
  * ``compare_blp_ng`` — side-by-side diagnostic across channels

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

from eternal_nm_sim.core import (
    blp_measure,
    compare_blp_ng,
    hall_channel,
    pauli_channel,
)

__all__ = [
    "blp_measure",
    "compare_blp_ng",
    "hall_channel",
    "pauli_channel",
]

__version__ = "0.1.0"
__author__ = "DESVAUX G.J.Y."
__contact__ = "contact@hopenmind.com"
__license__ = "Apache-2.0 OR LicenseRef-HopenMind-Commercial"
