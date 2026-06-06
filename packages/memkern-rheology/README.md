# `memkern-rheology` — Maxwell-Wiechert adapter

[![Suite DOI](https://img.shields.io/badge/Suite_DOI-10.5281%2Fzenodo.19486927-c9a84c?style=for-the-badge&logo=doi&logoColor=white)](https://doi.org/10.5281/zenodo.19486927)
[![License](https://img.shields.io/badge/License-Apache--2.0_or_Commercial-3d7fff?style=for-the-badge)](../../LICENSE)

Rheology adapter for [`memkern`](../memkern). Fits the generalised
Maxwell (Wiechert) relaxation modulus

    G(t) = G_∞ + Σ_k G_k · exp(-t/τ_k)

from experimental ``(t, G(t))`` data via a Matrix-Pencil Prony
decomposition with optional MaxEnt-based order selection.

Same decomposition, rheology conventions: moduli ``G_k``, relaxation
times ``τ_k``, dynamic moduli ``G'(ω) / G''(ω)``.

## Install

```bash
pip install memkern-rheology
```

## Usage

```python
import numpy as np
from memkern_rheology import fit_maxwell_wiechert, storage_loss_moduli

# Measured relaxation modulus
t = np.linspace(0, 100, 1024)
G = ...                         # shape (1024,), real

# Auto-select K with the MaxEnt criterion (default)
result = fit_maxwell_wiechert(t, G)
print(result.n_modes, result.G_inf, result.G_k, result.tau_k)

# Forward: frequency-domain moduli
omega = np.logspace(-3, 3, 200)
G_storage, G_loss = storage_loss_moduli(
    omega, result.G_inf, result.G_k, result.tau_k,
)
```

## Order-selection methods

| Method | Selector | When to use |
|--------|---------|-------------|
| `"maxent"` *(default)* | Shannon entropy of singular-value weights, threshold 0.95 | Default. Detects when adding modes no longer increases information spread. |
| `"variance"` | Singular-value variance ratio, threshold 0.9999 | Conventional, matches most rheology software defaults. |
| `"manual"` | User-fixed `n_modes` | When you know the model order from prior knowledge. |

## Status

- 0.1.x — first public release, 11 tests passing.
- DOI: module-specific DOI to be minted; until then cite the suite DOI.

## Licence

Dual-licensed: Apache-2.0 for academic / non-commercial, proprietary
for commercial. See the suite root [LICENSE](../../LICENSE).
