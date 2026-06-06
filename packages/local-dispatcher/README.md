# `local-dispatcher`

Local-only parallelism dispatcher. **No external credentials, no
HPC account.** Detects CPU cores, GPU (CUDA / Metal / ROCm), RAM, and
available libraries (joblib, dask, cupy, torch) — picks a backend that
can run the problem **on the machine in front of you**.

Backends considered (in order of preference when applicable):
- `cupy-cuda`, `torch-mps`, `cupy-rocm` — local GPU
- `joblib-threadpool` — CPU parallel, ≥ 4 cores
- `dask-out-of-core` — RAM-constrained, chunked processing
- `serial-numpy` / `serial-memory-bound` — fallbacks

Escalates to `hpc-manifest` only if the problem cannot fit locally.

```python
from local_dispatcher import local_dispatcher_tool
verdict = local_dispatcher_tool.evaluate(problem)
print(verdict.diagnostic["backend"], verdict.diagnostic["hardware"])
```
