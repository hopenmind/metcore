"""Tests for local-dispatcher.

Focus on hardware-detection robustness (must not crash on any platform,
ever) and backend-selection logic (deterministic given a mock hw dict).

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
"""

from __future__ import annotations

import numpy as np

from hpc_triage import Problem, Tier, VerdictStatus
from local_dispatcher import detect_hardware, local_dispatcher_tool
from local_dispatcher.tool import _pick_backend


def _p(ram_need_gb=1.0, d=2, N=512):
    return Problem(
        spectral_density=lambda w: np.exp(-np.asarray(w, dtype=float) ** 2),
        system_hamiltonian=np.eye(d, dtype=complex),
        coupling_strength=0.1,
        n_time_steps=N,
        metadata={"ram_need_gb": ram_need_gb},
    )


# ──────────────────────────────────────────────────────────────────────────────
#  Hardware detection shape + cross-platform robustness
# ──────────────────────────────────────────────────────────────────────────────

def test_detect_hardware_returns_expected_keys():
    hw = detect_hardware()
    for k in ("cpu", "ram", "gpu", "libraries"):
        assert k in hw
    assert hw["cpu"]["logical_cores"] >= 1
    assert hw["ram"]["total_gb"] > 0
    for lib in ("joblib", "dask", "cupy", "torch", "numba", "ray"):
        assert lib in hw["libraries"]
        assert isinstance(hw["libraries"][lib], bool)


def test_detect_hardware_idempotent():
    a = detect_hardware()
    b = detect_hardware()
    # cores/ram don't change between consecutive calls
    assert a["cpu"] == b["cpu"]
    assert a["ram"]["total_gb"] == b["ram"]["total_gb"]


# ──────────────────────────────────────────────────────────────────────────────
#  Backend picker — deterministic on mock hardware dicts
# ──────────────────────────────────────────────────────────────────────────────

def _mock_hw(ram_gb=16.0, cores=8, cuda=False, metal=False, rocm=False,
             libs=None):
    libs = libs or {}
    default_libs = {"joblib": False, "dask": False, "cupy": False,
                    "torch": False, "numba": False, "ray": False}
    default_libs.update(libs)
    return {
        "cpu":       {"logical_cores": cores, "physical_cores": cores,
                      "architecture": "x86_64", "platform": "Linux"},
        "ram":       {"total_gb": ram_gb, "detected_by": "mock"},
        "gpu":       {"cuda": cuda, "metal": metal, "rocm": rocm, "details": []},
        "libraries": default_libs,
    }


def test_picker_prefers_cuda_when_available():
    hw = _mock_hw(cuda=True, libs={"cupy": True})
    assert _pick_backend(hw, ram_need_gb=1.0) == "cupy-cuda"


def test_picker_prefers_joblib_when_cpu_and_no_gpu():
    hw = _mock_hw(cores=16, libs={"joblib": True})
    assert _pick_backend(hw, ram_need_gb=1.0) == "joblib-threadpool"


def test_picker_falls_back_serial_on_small_cpu():
    hw = _mock_hw(cores=2, libs={"joblib": True})
    assert _pick_backend(hw, ram_need_gb=1.0) == "serial-numpy"


def test_picker_out_of_core_when_ram_tight_and_dask_present():
    hw = _mock_hw(ram_gb=2.0, libs={"dask": True})
    assert _pick_backend(hw, ram_need_gb=10.0) == "dask-out-of-core"


def test_picker_memory_bound_when_ram_tight_no_dask():
    hw = _mock_hw(ram_gb=2.0)
    assert _pick_backend(hw, ram_need_gb=10.0) == "serial-memory-bound"


# ──────────────────────────────────────────────────────────────────────────────
#  Tool evaluation
# ──────────────────────────────────────────────────────────────────────────────

def test_tool_protocol_attributes():
    assert local_dispatcher_tool.name == "local-dispatcher"
    assert local_dispatcher_tool.tier == Tier.LAPTOP


def test_tool_evaluation_returns_verdict_with_hw():
    v = local_dispatcher_tool.evaluate(_p(ram_need_gb=0.1))
    assert v.status == VerdictStatus.ESCALATE
    assert "hardware" in v.diagnostic
    assert v.tier in (Tier.LAPTOP, Tier.WORKSTATION, Tier.GPU_CLOUD, Tier.HPC)


def test_tool_escalates_to_hpc_when_ram_need_exceeds_local():
    # Force RAM need beyond any reasonable laptop
    v = local_dispatcher_tool.evaluate(_p(ram_need_gb=9999.0))
    assert v.tier == Tier.HPC
    assert v.next_tool == "hpc-manifest"
