# `hpc-manifest`

Right-sized SLURM / PBS / LSF submission-script generator. Last tool
in the triage ladder — invoked when HPC is confirmed necessary.

Uses the cost / memory estimates from upstream (hpc-oracle,
bench-extrap), applies configurable safety margins, writes
`submit.sbatch` / `submit.pbs` / `submit.lsf`.

```python
from hpc_manifest import HPCManifestTool
tool = HPCManifestTool(scheduler="slurm", n_cores=64, partition="debug",
                       email="me@lab.org")
verdict = tool.evaluate(problem)
print(verdict.result["script_path"])   # → ./submit.sbatch
```
