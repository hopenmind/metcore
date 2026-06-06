"""ng-vol — Geometric non-Markovianity measure via Liouville-space volume.

Implements the measure introduced in

    G.J.Y. Desvaux, "Nakajima-Zwanzig non-Markovian extension with
    falsifiable hypotheses", §3.6 (definition 3.12, theorem 3.13):

                          1     ∞  ⎡dV(t)⎤
        N_G = sup_S₀  ─────  ∫   ⎢─────⎥    dt          (Eq. 26)
                      V(0)   0   ⎣ dt  ⎦_+

where V(t) is the Hilbert-Schmidt volume of the simplex obtained by
evolving an initial set S₀ = {ρ_1, …, ρ_n} through the channel Φ_{t,0}
and [x]_+ = max(x, 0).

Faithfulness:  N_G = 0  ⇔  Φ is CP-divisible.
Computability: for a qubit (d=2) the supremum is achieved by the
vertices of a regular tetrahedron on the Bloch sphere.

Public surface (0.1.x):
  * ``ng_from_bloch_matrices`` — N_G for a qubit channel supplied as the
    time-indexed 3×3 affine map on the Bloch vector.
  * ``ng_from_states``        — N_G for any d via the simplex-volume
    integral on vectorised states.
  * ``bloch_tetrahedron``     — the regular-tetrahedron initial
    simplex that achieves the supremum at d=2.
  * Channel helpers:
      ``dephasing_channel``, ``amplitude_damping_channel``,
      ``depolarizing_channel``, ``nonmarkovian_revival_channel``.

[NOVEL] Atomic contribution of the Hope 'n Mind Scientific Suite.
See ``docs/DOI_REGISTRY.md`` at the suite root — level 3.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

from obliquity_ng.channels import (
    amplitude_damping_channel,
    depolarizing_channel,
    dephasing_channel,
    nonmarkovian_revival_channel,
)
from obliquity_ng.measure import (
    bloch_tetrahedron,
    ng_from_bloch_matrices,
    ng_from_states,
)

__all__ = [
    "amplitude_damping_channel",
    "bloch_tetrahedron",
    "depolarizing_channel",
    "dephasing_channel",
    "ng_from_bloch_matrices",
    "ng_from_states",
    "nonmarkovian_revival_channel",
]

__version__ = "0.1.0"
__author__ = "DESVAUX G.J.Y."
__contact__ = "contact@hopenmind.com"
__license__ = "Apache-2.0 OR LicenseRef-HopenMind-Commercial"
