"""Tests for hpc-manifest."""

from __future__ import annotations

import numpy as np
import pytest

from hpc_manifest import (
    HPCManifestTool,
    hpc_manifest_tool,
    render_pbs,
    render_slurm,
)
from hpc_triage import Problem, Tier, VerdictStatus


def _p(seconds=3600.0, ram_gb=16.0, job="test-job",
       command="python run.py"):
    return Problem(
        spectral_density=lambda w: np.exp(-np.asarray(w, dtype=float) ** 2),
        system_hamiltonian=np.eye(2, dtype=complex),
        coupling_strength=0.1,
        metadata={"cost_seconds": seconds, "ram_gb": ram_gb,
                  "job_name": job, "command": command},
    )


def test_render_slurm_shape():
    s = render_slurm(job_name="x", n_cores=4, mem_gb=8,
                     hours=1, minutes=0, seconds=0,
                     command="echo ok")
    assert s.startswith("#!/usr/bin/env bash")
    assert "--job-name=x" in s
    assert "--cpus-per-task=4" in s
    assert "--mem=8G" in s
    assert "01:00:00" in s
    assert "echo ok" in s


def test_render_pbs_shape():
    s = render_pbs(job_name="x", n_cores=4, mem_gb=8,
                   hours=2, minutes=30, seconds=0,
                   command="echo ok")
    assert "#PBS -N x" in s
    assert "ncpus=4" in s
    assert "mem=8gb" in s
    assert "02:30:00" in s


def test_render_slurm_email_optional():
    no = render_slurm(job_name="x", n_cores=1, mem_gb=1, hours=0, minutes=5,
                      seconds=0, command="true")
    with_ = render_slurm(job_name="x", n_cores=1, mem_gb=1, hours=0, minutes=5,
                         seconds=0, command="true", email="me@lab.org")
    assert "--mail-type" not in no
    assert "--mail-type" in with_


def test_tool_writes_sbatch_file(tmp_path):
    tool = HPCManifestTool(scheduler="slurm", outdir=tmp_path)
    v = tool.evaluate(_p(seconds=120, ram_gb=4))
    assert v.status == VerdictStatus.SOLVED
    assert v.tier == Tier.HPC
    path = tmp_path / "submit.sbatch"
    assert path.is_file()
    body = path.read_text(encoding="utf-8")
    assert "#SBATCH" in body


def test_tool_writes_pbs_file(tmp_path):
    tool = HPCManifestTool(scheduler="pbs", outdir=tmp_path)
    v = tool.evaluate(_p())
    assert v.status == VerdictStatus.SOLVED
    assert (tmp_path / "submit.pbs").is_file()


def test_tool_margins_inflate_request(tmp_path):
    tool_tight = HPCManifestTool(
        scheduler="slurm", outdir=tmp_path,
        time_margin=1.0, mem_margin=1.0,
    )
    tool_loose = HPCManifestTool(
        scheduler="slurm", outdir=tmp_path,
        time_margin=3.0, mem_margin=3.0,
    )
    p = _p(seconds=600, ram_gb=4)
    v_tight = tool_tight.evaluate(p)
    v_loose = tool_loose.evaluate(p)
    assert v_loose.diagnostic["mem_gb"] >= v_tight.diagnostic["mem_gb"]


def test_default_tool_smoke(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    v = hpc_manifest_tool.evaluate(_p())
    assert v.status == VerdictStatus.SOLVED


def test_tool_protocol_attributes():
    assert hpc_manifest_tool.name == "hpc-manifest"
    assert hpc_manifest_tool.tier == Tier.HPC
