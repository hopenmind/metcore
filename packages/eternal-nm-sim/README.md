# `eternal-nm-sim` — canonical fixtures for eternal non-Markovianity

[![Suite DOI](https://img.shields.io/badge/Suite_DOI-10.5281%2Fzenodo.19486927-c9a84c?style=for-the-badge&logo=doi&logoColor=white)](https://doi.org/10.5281/zenodo.19486927)
[![License](https://img.shields.io/badge/License-Apache--2.0_or_Commercial-3d7fff?style=for-the-badge)](../../LICENSE)

Canonical reference channels and measures for testing non-Markovianity
witnesses. Companion package to [`ng-vol`](../ng-vol).

## Why this exists

Non-Markovianity measures differ in what they detect. The Hall 2014
Pauli channel

    γ_x = γ_y = 1 ,     γ_z(t) = -tanh(t)

is the canonical counter-example that separates *information backflow*
(BLP) from *CP-divisibility* (RHP-class). `eternal-nm-sim` ships:

- **`hall_channel()`** — the Hall 2014 Pauli channel.
- **`pauli_channel(γ_x, γ_y, γ_z)`** — general Pauli-channel builder.
- **`blp_measure(M, t)`** — trace-distance-revival (BLP) measure.
- **`compare_blp_ng(channels, t)`** — side-by-side diagnostic.

## Quick diagnostic

```python
import numpy as np
from eternal_nm_sim import compare_blp_ng, hall_channel
from ng_vol import dephasing_channel, nonmarkovian_revival_channel

t = np.linspace(0.0, 10.0, 1024)
table = compare_blp_ng({
    "dephasing": dephasing_channel(0.5),
    "hall":      hall_channel(),
    "revival":   nonmarkovian_revival_channel(gamma=0.3, omega=2.0),
}, t)
# {"dephasing": {"BLP": ~0, "N_G": ~0},
#  "hall":      {"BLP": ~0, "N_G": ~0},      ← eternal-NM invisible to both
#  "revival":   {"BLP": > 0, "N_G": > 0}}    ← both detect revival
```

## What this teaches

- **Markovian channels**: BLP = 0 and `N_G` = 0 — faithfulness both ways.
- **Revival-type non-Markovianity**: both measures detect it (they see
  information/volume flowing back).
- **Hall's eternal non-Markovianity**: γ_z < 0 makes the intermediate
  map Φ_{t,s} non-CP, yet the full channel Φ_t contracts monotonically
  in *every* pair distance and in the Hilbert-Schmidt volume. Both BLP
  and the volume-based `N_G` return 0 on it. Detecting this regime
  requires a finer measure (RHP / trace-norm of the Choi derivative).
  That's not a bug — it's the precise operational scope of each
  witness.

This lets you test any new non-Markovianity measure against a
well-known benchmark in two lines.

## Paper reference

- Hall, M.J.W., Cresser, J.D., Li, L., Andersson, E., 2014.
  *Canonical form of master equations and characterization of
  non-Markovianity*. PRA 89, 042120.
- Breuer, H.-P., Laine, E.-M., Piilo, J., 2009.
  *Measure for the degree of non-Markovian behavior of quantum
  processes in open systems*. PRL 103, 210401.

## Licence

Dual-licensed: Apache-2.0 for academic / non-commercial, proprietary
for commercial. See the suite root [LICENSE](../../LICENSE).
