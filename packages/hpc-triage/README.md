# `hpc-triage` — do you actually need a supercomputer?

[![Suite DOI](https://img.shields.io/badge/Suite_DOI-10.5281%2Fzenodo.19486927-c9a84c?style=for-the-badge&logo=doi&logoColor=white)](https://doi.org/10.5281/zenodo.19486927)
[![License](https://img.shields.io/badge/License-Apache--2.0_or_Commercial-3d7fff?style=for-the-badge)](../../LICENSE)

Triage toolkit for PhD students and researchers working on
non-Markovian open-quantum-system problems. Answers one question
upfront, with evidence:

> "Do I actually need HPC for this problem, or can it run on my laptop?"

## Concept

Every triage tool in the Hope 'n Mind Suite implements the same
three-line protocol defined in this package:

```python
class TriageTool(Protocol):
    name: str
    tier: Tier
    def evaluate(self, problem: Problem) -> Verdict: ...
```

Given a `Problem` (spectral density, system Hamiltonian, coupling,
target accuracy), each tool returns a `Verdict`:

- `SOLVED` — the problem was answered at this tier, stop.
- `ESCALATE` — this tier is insufficient, try the next tool.
- `BLOCKED` — no tier in the ladder can handle it; give up honestly.
- `ABORT` — bad input or internal error; human needed.

`cascade()` runs an ordered ladder of tools until a terminal verdict.

## Install

```bash
pip install hpc-triage
```

## Usage

```python
import numpy as np
from hpc_triage import Problem, cascade
from kernel_audit import kernel_audit_tool            # ← future sibling package
from memkern_ladder import memkern_ladder_tool
from hpc_oracle import hpc_oracle_tool
from bench_extrap import bench_extrap_tool
from cloud_dispatcher import cloud_dispatcher_tool
from hpc_manifest import hpc_manifest_tool

problem = Problem(
    spectral_density    = lambda w: 0.3 * w**2 * np.exp(-w**2),
    system_hamiltonian  = np.diag([0.0, 1.0]),
    coupling_strength   = 0.1,
    temperature         = 0.05,
    t_max               = 20.0,
    n_time_steps        = 2048,
    target_accuracy     = 1e-4,
)

ladder = [
    kernel_audit_tool,
    memkern_ladder_tool,
    hpc_oracle_tool,
    bench_extrap_tool,
    cloud_dispatcher_tool,
    hpc_manifest_tool,
]

verdict = cascade(problem, ladder)
```

Typical output on a laptop-tractable problem:

```
[kernel-audit         ] escalate @ laptop       K ≤ 20 modes, laptop ok, proceed
[memkern-ladder       ] solved   @ laptop       level 3 (Prony-pseudomode) converges at 1.4e-5
```

Typical output on a genuinely HPC-bound problem:

```
[kernel-audit         ] escalate @ workstation  K ≈ 180 modes, laptop insufficient
[memkern-ladder       ] escalate @ workstation  level 3 did not converge at K_max=50
[hpc-oracle           ] escalate @ hpc          RAM required ≈ 420 GB, HPC tier
[bench-extrap         ] escalate @ hpc          extrapolated wall-time 73 h on 64 cores
[cloud-dispatcher     ] escalate @ hpc          problem too large for single-GPU cloud tier
[hpc-manifest         ] solved   @ hpc          SLURM script written to submit.sbatch
```

## Why this abstraction first, tools after

Putting the contract down before the six implementations means:

- Every tool is ~20 lines of pure domain logic; orchestration is in
  `cascade()`, not in each tool.
- Tools are independently testable with mocked `Problem`s.
- New tiers (e.g. a quantum emulator tier) slot in without touching
  existing tools.
- The cascade itself is six lines, readable at a glance.

## Roadmap

The six sibling packages that implement `TriageTool` are:

| Tool | Tier | Role |
|------|------|------|
| `kernel-audit`      | laptop/workstation | predicts required Prony order K from J(ω) |
| `memkern-ladder`    | laptop/workstation | tries 5 approximation levels, stops when converged |
| `hpc-oracle`        | all                | cost & RAM estimator per tier |
| `bench-extrap`      | all                | runs 3 small sizes, extrapolates scaling law |
| `cloud-dispatcher`  | gpu_cloud          | ships to Modal/Colab/vast.ai if laptop insufficient |
| `hpc-manifest`      | hpc                | generates SLURM/PBS submission script with right resources |

Total implementation effort once this abstraction is in place:
**~25 hours** of straightforward code.

## Status

0.1.x — abstraction + cascade + tests (no triage tools yet; they ship
as sibling packages).

## Licence

Dual-licensed: Apache-2.0 for academic / non-commercial, proprietary
for commercial. See the suite root [LICENSE](../../LICENSE).
