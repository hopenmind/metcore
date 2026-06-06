# `memkern` — Memory-kernel engine (domain-agnostic)

[![Suite DOI](https://img.shields.io/badge/Suite_DOI-10.5281%2Fzenodo.19486927-c9a84c?style=for-the-badge&logo=doi&logoColor=white)](https://doi.org/10.5281/zenodo.19486927)
[![License](https://img.shields.io/badge/License-Apache--2.0_or_Commercial-3d7fff?style=for-the-badge)](../../LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)]()

*A module-specific DOI will be minted with the `0.1.0` PyPI release. Until
then the suite DOI above covers citation of this module.*

The generic numerical core of the [Hope 'n Mind Scientific Suite](https://github.com/hopenmind/hopenmind-suite).

`memkern` provides the primitives used by every tool in the suite that
models a system with a finite memory kernel — regardless of the domain.
The same decomposition applies to:

| Domain | Kernel interpretation |
|--------|-----------------------|
| Open quantum systems | bath correlation ``C(τ)`` in Nakajima-Zwanzig memory superoperator |
| Rheology / viscoelasticity | generalised Maxwell relaxation modulus ``G(t) = G∞ + Σ Gₖ exp(-t/τₖ)`` |
| Climate | impulse response function ``IRF(t)`` in simple climate models (MAGICC, FaIR) |
| Biology | calcium integration, gene regulation with translation lag, quorum sensing |
| Time series | exponential smoothing, ARMA-equivalent kernels |

## Install

```bash
pip install memkern
```

## What's in 0.1.x

```python
from memkern import prony_decompose, maxent_select_order, PronyResult

result = prony_decompose(tau, y)          # auto order via variance-ratio
result = prony_decompose(tau, y, n_exp=5) # fixed K

# Pick the order yourself with the MaxEnt criterion (NOVEL):
K = maxent_select_order(result.singular_values, entropy_ratio_threshold=0.95)
```

### The MaxEnt order selector (novel)

Given the singular spectrum ``σ₁ ≥ σ₂ ≥ …`` of the Hankel pencil, define
the weight distribution ``pᵢ = σᵢ²/Σ σⱼ²`` and its Shannon entropy ``H``.
The **effective number of modes** is ``N_eff = exp(H)`` (the perplexity
of the spectrum). `maxent_select_order` returns the smallest ``K`` such
that the truncated-spectrum entropy captures at least
``entropy_ratio_threshold`` (default 0.95) of the full entropy.

Difference from the conventional variance-ratio:

- **Variance-ratio** keeps dominant modes, may under-pick when residual
  structure is spread across many small modes.
- **MaxEnt-ratio** detects when *adding another mode no longer increases
  the effective spread of information*, a more honest measure of the
  least-biased ``K``.

The connection to Jaynes's principle is direct: among all Prony
decompositions that fit the data within tolerance, the one whose
coefficients carry maximum entropy is the least biased.

## Roadmap

- FFT-based bath / auto-correlation transform (extraction from
  BoltZ-Kernel in 0.2.x).
- Pseudomode (TCL2-style) reduction of exponential kernels to an ODE
  system.
- Domain adapters: rheology (Maxwell-Wiechert fit), bio (calcium,
  translation-lag gene regulation), climate (IRF fit of GCM output).

## Licence

Dual-licensed: Apache-2.0 for academic / non-commercial use, proprietary
for commercial use. See the suite-root [LICENSE](../../LICENSE).

## Citation

See [`CITATION.cff`](./CITATION.cff) or:

```bibtex
@software{desvaux_memkern_2026,
  author  = {DESVAUX, G.J.Y.},
  title   = {memkern: Memory-kernel engine (domain-agnostic)},
  year    = {2026},
  version = {0.1.0},
  url     = {https://github.com/hopenmind/hopenmind-suite/tree/main/packages/memkern},
  note    = {Part of the Hope 'n Mind Scientific Suite, DOI 10.5281/zenodo.19486927.},
}
```
