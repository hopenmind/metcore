"""SLURM / PBS / LSF script generator."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from hpc_triage import Problem, Tier, Verdict, VerdictStatus


Scheduler = Literal["slurm", "pbs", "lsf"]


# ──────────────────────────────────────────────────────────────────────────────
#  Sizing with safety margin
# ──────────────────────────────────────────────────────────────────────────────

def _round_time(seconds: float, margin: float = 1.2) -> tuple[int, int, int]:
    """Convert seconds (with safety margin) to (HH, MM, SS)."""
    total = int(seconds * margin) + 60
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return h, m, s


def _round_mem_gb(gb: float, margin: float = 1.3) -> int:
    """Round memory up to nearest GB with safety margin."""
    return max(1, int((gb * margin) + 1))


# ──────────────────────────────────────────────────────────────────────────────
#  Script templates
# ──────────────────────────────────────────────────────────────────────────────

def render_slurm(*, job_name: str, n_cores: int, mem_gb: int,
                 hours: int, minutes: int, seconds: int,
                 command: str,
                 partition: str = "compute",
                 email: str | None = None) -> str:
    email_lines = (f"#SBATCH --mail-type=END,FAIL\n"
                   f"#SBATCH --mail-user={email}\n") if email else ""
    return (
        f"#!/usr/bin/env bash\n"
        f"#SBATCH --job-name={job_name}\n"
        f"#SBATCH --partition={partition}\n"
        f"#SBATCH --nodes=1\n"
        f"#SBATCH --ntasks=1\n"
        f"#SBATCH --cpus-per-task={n_cores}\n"
        f"#SBATCH --mem={mem_gb}G\n"
        f"#SBATCH --time={hours:02d}:{minutes:02d}:{seconds:02d}\n"
        f"#SBATCH --output={job_name}.%j.out\n"
        f"#SBATCH --error={job_name}.%j.err\n"
        f"{email_lines}"
        f"\n"
        f"set -euo pipefail\n"
        f"module load python/3.12 || true\n"
        f"cd \"$SLURM_SUBMIT_DIR\"\n"
        f"\n"
        f"{command}\n"
    )


def render_pbs(*, job_name: str, n_cores: int, mem_gb: int,
               hours: int, minutes: int, seconds: int,
               command: str, queue: str = "normal") -> str:
    return (
        f"#!/usr/bin/env bash\n"
        f"#PBS -N {job_name}\n"
        f"#PBS -q {queue}\n"
        f"#PBS -l select=1:ncpus={n_cores}:mem={mem_gb}gb\n"
        f"#PBS -l walltime={hours:02d}:{minutes:02d}:{seconds:02d}\n"
        f"#PBS -o {job_name}.${{PBS_JOBID}}.out\n"
        f"#PBS -e {job_name}.${{PBS_JOBID}}.err\n"
        f"\n"
        f"set -euo pipefail\n"
        f"cd \"$PBS_O_WORKDIR\"\n"
        f"\n"
        f"{command}\n"
    )


def render_lsf(*, job_name: str, n_cores: int, mem_gb: int,
               hours: int, minutes: int, seconds: int,
               command: str, queue: str = "normal") -> str:
    return (
        f"#!/usr/bin/env bash\n"
        f"#BSUB -J {job_name}\n"
        f"#BSUB -q {queue}\n"
        f"#BSUB -n {n_cores}\n"
        f"#BSUB -M {mem_gb * 1024}\n"
        f"#BSUB -W {hours:02d}:{minutes:02d}\n"
        f"#BSUB -o {job_name}.%J.out\n"
        f"#BSUB -e {job_name}.%J.err\n"
        f"\n"
        f"set -euo pipefail\n"
        f"{command}\n"
    )


# ──────────────────────────────────────────────────────────────────────────────
#  Tool
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class HPCManifestTool:
    """Always SOLVED — emits the submission script the user needs."""

    scheduler: Scheduler = "slurm"
    n_cores: int = 32
    partition: str = "compute"
    email: str | None = None
    time_margin: float = 1.2
    mem_margin: float = 1.3
    outdir: Path = field(default_factory=lambda: Path("."))

    name: str = "hpc-manifest"
    tier: Tier = Tier.HPC

    def evaluate(self, problem: Problem) -> Verdict:
        # Pull cost estimates from metadata (populated by upstream tools)
        seconds = float(problem.metadata.get("cost_seconds", 3600.0))
        ram_gb = float(problem.metadata.get("ram_gb", 16.0))

        h, m, s = _round_time(seconds, margin=self.time_margin)
        mem = _round_mem_gb(ram_gb, margin=self.mem_margin)

        job_name = str(problem.metadata.get("job_name", "hopenmind-job"))
        command = str(problem.metadata.get("command",
                                           "python -m hopenmind.run --help"))

        if self.scheduler == "slurm":
            body = render_slurm(
                job_name=job_name, n_cores=self.n_cores, mem_gb=mem,
                hours=h, minutes=m, seconds=s,
                command=command, partition=self.partition,
                email=self.email,
            )
            ext = ".sbatch"
        elif self.scheduler == "pbs":
            body = render_pbs(
                job_name=job_name, n_cores=self.n_cores, mem_gb=mem,
                hours=h, minutes=m, seconds=s, command=command,
            )
            ext = ".pbs"
        else:
            body = render_lsf(
                job_name=job_name, n_cores=self.n_cores, mem_gb=mem,
                hours=h, minutes=m, seconds=s, command=command,
            )
            ext = ".lsf"

        path = Path(self.outdir) / f"submit{ext}"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            return Verdict(status=VerdictStatus.ABORT, tier=Tier.HPC,
                           message=f"failed to write script: {exc!r}")

        return Verdict(
            status=VerdictStatus.SOLVED, tier=Tier.HPC,
            message=f"{self.scheduler.upper()} script written to {path}",
            result={"script_path": str(path), "script_body": body},
            diagnostic={
                "scheduler": self.scheduler,
                "job_name":  job_name,
                "cores":     self.n_cores,
                "mem_gb":    mem,
                "walltime":  f"{h:02d}:{m:02d}:{s:02d}",
            },
        )


hpc_manifest_tool = HPCManifestTool()
