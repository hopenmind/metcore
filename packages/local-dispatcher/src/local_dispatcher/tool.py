"""Local hardware detection + backend selection."""

from __future__ import annotations

import importlib
import os
import platform
import shutil
from dataclasses import dataclass, field

import numpy as np

from hpc_triage import Problem, Tier, Verdict, VerdictStatus


# ──────────────────────────────────────────────────────────────────────────────
#  Hardware detection — zero external deps, graceful fallbacks
# ──────────────────────────────────────────────────────────────────────────────

def _module_available(name: str) -> bool:
    try:
        importlib.import_module(name)
        return True
    except Exception:
        return False


def _detect_cpu() -> dict:
    logical = os.cpu_count() or 1
    try:
        import multiprocessing
        physical = multiprocessing.cpu_count()
    except Exception:
        physical = logical
    return {
        "logical_cores":  int(logical),
        "physical_cores": int(physical),
        "architecture":   platform.machine(),
        "platform":       platform.system(),
    }


def _detect_ram() -> dict:
    """Try psutil; fall back to sysconf / hard default."""
    total_bytes = None
    if _module_available("psutil"):
        try:
            import psutil
            vm = psutil.virtual_memory()
            total_bytes = vm.total
        except Exception:
            total_bytes = None
    if total_bytes is None:
        # POSIX-only fallback
        try:
            pages = os.sysconf("SC_PHYS_PAGES")
            page_size = os.sysconf("SC_PAGE_SIZE")
            total_bytes = pages * page_size
        except Exception:
            total_bytes = 8 * (1024 ** 3)   # conservative 8 GB default
    return {
        "total_gb":      total_bytes / (1024 ** 3),
        "detected_by":   "psutil" if _module_available("psutil") else "sysconf-or-default",
    }


def _detect_gpu() -> dict:
    """Probe CUDA via shutil (nvidia-smi), Metal/MPS via torch, ROCm via rocm-smi."""
    info: dict = {"cuda": False, "metal": False, "rocm": False, "details": []}

    # CUDA
    if shutil.which("nvidia-smi"):
        info["cuda"] = True
        info["details"].append("nvidia-smi present")

    # Metal/MPS (macOS)
    if platform.system() == "Darwin":
        if _module_available("torch"):
            try:
                import torch
                if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                    info["metal"] = True
                    info["details"].append("MPS via torch")
            except Exception:
                pass

    # ROCm
    if shutil.which("rocm-smi"):
        info["rocm"] = True
        info["details"].append("rocm-smi present")

    return info


def _detect_libraries() -> dict:
    return {
        "joblib":  _module_available("joblib"),
        "dask":    _module_available("dask"),
        "cupy":    _module_available("cupy"),
        "torch":   _module_available("torch"),
        "numba":   _module_available("numba"),
        "ray":     _module_available("ray"),
    }


def detect_hardware() -> dict:
    """One-shot snapshot of local resources."""
    return {
        "cpu":       _detect_cpu(),
        "ram":       _detect_ram(),
        "gpu":       _detect_gpu(),
        "libraries": _detect_libraries(),
    }


# ──────────────────────────────────────────────────────────────────────────────
#  Backend recommendation
# ──────────────────────────────────────────────────────────────────────────────

def _pick_backend(hw: dict, ram_need_gb: float) -> str:
    """Choose the best local backend for a given RAM need."""
    if hw["ram"]["total_gb"] < ram_need_gb:
        # Won't fit in RAM at all — still pick dask if installed, else serial
        if hw["libraries"]["dask"]:
            return "dask-out-of-core"
        return "serial-memory-bound"

    # GPU path: only if cupy/torch is present AND the user's dtypes fit
    if hw["gpu"]["cuda"] and hw["libraries"]["cupy"]:
        return "cupy-cuda"
    if hw["gpu"]["metal"] and hw["libraries"]["torch"]:
        return "torch-mps"
    if hw["gpu"]["rocm"] and hw["libraries"]["cupy"]:
        return "cupy-rocm"

    # CPU-parallel path
    if hw["libraries"]["joblib"] and hw["cpu"]["logical_cores"] >= 4:
        return "joblib-threadpool"

    return "serial-numpy"


# ──────────────────────────────────────────────────────────────────────────────
#  Tool
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class LocalDispatcherTool:
    """Inspects the local machine, reports the backend + tier verdict."""

    ram_safety_factor: float = 1.3   # ask 30 % headroom above estimated RAM
    name: str = "local-dispatcher"
    tier: Tier = Tier.LAPTOP

    def evaluate(self, problem: Problem) -> Verdict:
        hw = detect_hardware()

        # Pull cost estimate from an upstream tool if available
        ram_needed_gb = float(problem.metadata.get("ram_need_gb", 1.0))
        ram_needed_gb *= self.ram_safety_factor

        backend = _pick_backend(hw, ram_needed_gb)
        fits = hw["ram"]["total_gb"] >= ram_needed_gb

        if backend.startswith("cupy") or backend.startswith("torch"):
            tier = Tier.GPU_CLOUD    # local GPU → GPU_CLOUD tier bucket
            msg = f"local GPU backend: {backend}"
        elif backend == "dask-out-of-core":
            # Out-of-core is realistic up to a few times local RAM; beyond
            # that the spill traffic dominates and only HPC makes sense.
            if ram_needed_gb > 4.0 * hw["ram"]["total_gb"]:
                return Verdict(
                    status=VerdictStatus.ESCALATE, tier=Tier.HPC,
                    message=(f"need {ram_needed_gb:.1f} GB > 4x local RAM "
                             f"{hw['ram']['total_gb']:.1f} GB: out-of-core unrealistic"),
                    diagnostic={"hardware": hw, "backend": backend,
                                "ram_need_gb": ram_needed_gb},
                    next_tool="hpc-manifest",
                )
            tier = Tier.WORKSTATION
            msg = f"local out-of-core: {backend} (RAM tight)"
        elif backend == "joblib-threadpool":
            tier = Tier.LAPTOP if hw["cpu"]["logical_cores"] <= 12 else Tier.WORKSTATION
            msg = f"{backend} on {hw['cpu']['logical_cores']} cores"
        elif backend == "serial-memory-bound":
            return Verdict(
                status=VerdictStatus.ESCALATE, tier=Tier.HPC,
                message=f"local RAM {hw['ram']['total_gb']:.1f} GB < need {ram_needed_gb:.1f} GB, no dask",
                diagnostic={"hardware": hw, "backend": backend,
                            "ram_need_gb": ram_needed_gb},
                next_tool="hpc-manifest",
            )
        else:
            tier = Tier.LAPTOP
            msg = f"serial numpy on {hw['cpu']['logical_cores']} cores"

        # This tool is a router in the triage cascade: it always escalates to
        # the next tool (memkern-ladder locally, hpc-manifest otherwise).
        status = VerdictStatus.ESCALATE
        return Verdict(
            status=status, tier=tier,
            message=msg,
            memory_estimate_gb=ram_needed_gb,
            diagnostic={
                "hardware":     hw,
                "backend":      backend,
                "ram_need_gb":  ram_needed_gb,
                "fits_locally": fits,
            },
            next_tool="memkern-ladder" if fits else "hpc-manifest",
        )


local_dispatcher_tool = LocalDispatcherTool()
