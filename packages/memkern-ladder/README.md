# `memkern-ladder`

**3 honest approximation levels, ordered from cheapest to most accurate.**

| Level | Method | Wall-clock (laptop) |
|-------|--------|---------------------|
| 1 | Markovian Lindblad (analytical, Fermi golden rule) | ms |
| 2 | Born-Markov + 1st-order NZ correction | s |
| 3 | Prony-pseudomode ODE system (via `memkern`) | seconds |

Stops at the first level whose residual vs the next level is below
`problem.target_accuracy`. When level 3 is reached and the data
suggests HEOM territory, the verdict carries a hint pointing to
`hpc-oracle` for HPC-tier sizing — we do **not** pretend HEOM or
path-integral are part of this ladder. Three real levels, no
placeholders.

## Usage

```python
from hpc_triage import Problem, cascade
from memkern_ladder import memkern_ladder_tool

verdict = cascade(problem, [memkern_ladder_tool, ...])
print(verdict.diagnostic["level"])   # 1, 2, or 3
population = verdict.result["population"]
```
