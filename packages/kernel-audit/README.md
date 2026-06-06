# `kernel-audit` — pre-flight hardware-tier estimator

[![Suite DOI](https://img.shields.io/badge/Suite_DOI-10.5281%2Fzenodo.19486927-c9a84c?style=for-the-badge&logo=doi&logoColor=white)](https://doi.org/10.5281/zenodo.19486927)

First tool of the [HPC-triage](../hpc-triage) ladder. Given a
spectral density J(ω), it answers in seconds:

> "Roughly how many Prony modes K does your bath actually need, and
> what hardware tier does that imply?"

## Classification (overridable)

| Effective K | Tier | Interpretation |
|-------------|------|----------------|
| ≤ 10        | LAPTOP      | Prony-pseudomode fits in ≈ 16 GB RAM |
| (10, 50]    | WORKSTATION | Still tractable with 64-256 GB RAM |
| > 50        | HPC         | Full HEOM or path-integral likely needed |

## Install

```bash
pip install kernel-audit
```

## Usage

As part of a `hpc_triage.cascade(...)` ladder (normal path):

```python
from hpc_triage import Problem, cascade
from kernel_audit import kernel_audit_tool

verdict = cascade(problem, [kernel_audit_tool, ...])
```

Or standalone:

```python
from kernel_audit import KernelAuditTool
tool = KernelAuditTool(laptop_max_K=10, workstation_max_K=50)
v = tool.evaluate(problem)
print(v.tier, v.diagnostic["K_effective"])
```

Always returns `ESCALATE` — kernel-audit is an auditor, not a solver.
The `tier` field is the hint the cascade downstream consumes to pick
the next tool (memkern-ladder, hpc-oracle, etc.).

## How it works

1. Samples J(ω) on an ω grid up to a Nyquist-compliant cutoff.
2. Computes the zero-temperature bath correlation C(τ) by direct
   integration ∫ J(ω) e^{-iωτ} dω.
3. Runs a Matrix-Pencil Prony decomposition at `max_probe_K` (default
   60) to obtain the Hankel singular spectrum.
4. Applies `memkern.maxent_select_order` with an entropy threshold
   (default 0.95) to find the effective K.
5. Classifies K into a tier and returns an `ESCALATE` Verdict.

## Status

0.1.x — first public release, 10 tests covering canonical J(ω) shapes,
threshold overrides, and cascade integration.

## Licence

Dual-licensed: Apache-2.0 for academic / non-commercial, proprietary
for commercial. See the suite root [LICENSE](../../LICENSE).
