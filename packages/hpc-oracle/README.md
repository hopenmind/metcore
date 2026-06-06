# `hpc-oracle`

Cost & memory oracle for NZ problems. Given ``(K, d, N)`` from
upstream, predicts wall-time and RAM on 4 tiers (laptop, workstation,
GPU, HPC) via an analytical cost model.

```python
from hpc_oracle import hpc_oracle_tool
verdict = hpc_oracle_tool.evaluate(problem)
print(verdict.tier, verdict.cost_estimate_seconds, verdict.memory_estimate_gb)
```
