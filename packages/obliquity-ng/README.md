# `obliquity-ng` — Geometric non-Markovianity measure

[![Suite DOI](https://img.shields.io/badge/Suite_DOI-10.5281%2Fzenodo.19486927-c9a84c?style=for-the-badge&logo=doi&logoColor=white)](https://doi.org/10.5281/zenodo.19486927)
[![License](https://img.shields.io/badge/License-Apache--2.0_or_Commercial-3d7fff?style=for-the-badge)](../../LICENSE)

Faithful, qudit-general measure of quantum non-Markovianity based on
the evolution of the Hilbert-Schmidt simplex volume in Liouville space.

    N_G = sup_{S₀} (1/V(0)) · ∫₀^∞ [dV(t)/dt]_+ dt           (Eq. 26)

**Faithfulness:** `N_G = 0` iff the channel is CP-divisible.
**Computability:** for a qubit the supremum is achieved by the regular
tetrahedron inscribed in the Bloch sphere (Theorem 3.13.iii) — so a
single-point evaluation replaces the intractable optimisation over
state pairs required by BLP at d > 2.

## Install

```bash
pip install obliquity-ng
```

## Usage

```python
import numpy as np
from obliquity_ng import (
    nonmarkovian_revival_channel, dephasing_channel,
    ng_from_bloch_matrices,
)

t = np.linspace(0, 10, 1024)

# Markovian → N_G = 0
N = ng_from_bloch_matrices(dephasing_channel(0.5)(t), t)
# N ≈ 0

# Non-Markovian (Rabi revivals) → N_G > 0
N = ng_from_bloch_matrices(nonmarkovian_revival_channel(0.3, 2.0)(t), t)
# N > 0
```

### General-d path

```python
from obliquity_ng import ng_from_states

# states.shape == (T, n, d, d)  — n evolved ρ_k at each time
N = ng_from_states(states, t_grid)
```

## Why this measure

- **Faithful:** N_G = 0 ⇔ CP-divisibility, no false positives.
- **Tractable in high dimension:** BLP requires optimisation over all
  pairs of initial states; intractable for d > 2. N_G's supremum has a
  known analytic form at d = 2 (regular tetrahedron) and reduces to a
  single-determinant integral otherwise.
- **Detects eternal non-Markovianity:** N_G > 0 on channels where BLP
  incorrectly reports 0 (Hall et al. 2014 counter-example). The paired
  test fixture lives in the forthcoming `eternal-nm-sim` package.

## Paper reference

G.J.Y. Desvaux, *Nakajima-Zwanzig non-Markovian extension with
falsifiable hypotheses*, §3.6 Definition 3.12 (Eq. 26), Theorem 3.13.

## Status

- 0.1.x — first public release, 11 tests passing on Markovian null-cases,
  positive-N_G revival fixture, and general-d path consistency.
- DOI: module-specific DOI to be minted; until then cite the suite DOI.

## Licence

Dual-licensed: Apache-2.0 for academic / non-commercial, proprietary
for commercial. See the suite root [LICENSE](../../LICENSE).
