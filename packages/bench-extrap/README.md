# `bench-extrap`

Scaling-law extrapolator — runs a callable on 3 small sizes, fits
``t = a·n^b`` or ``t = a·exp(b·n)`` (picks best R²), extrapolates
wall-time at the target problem size, classifies into a tier.

```python
from bench_extrap import bench_extrap_tool
verdict = bench_extrap_tool.evaluate(problem)
print(verdict.cost_estimate_seconds, verdict.tier)
```
