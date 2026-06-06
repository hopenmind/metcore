"""
BoltZ-Kernel MCP server implementation (FastMCP-based).

Exposes:
  - boltz_run_comparison     — single NM-vs-Lindblad comparison on J(ω)
  - boltz_prony_decompose    — Matrix-Pencil exponential decomposition of C(τ)
  - boltz_bench              — reproducible reference benchmark (Phase B stub)
  - boltz_branding_show      — current persistent branding configuration
  - boltz_branding_set       — update persistent branding (all fields optional)
  - boltz_backends_info      — metadata about available solver backends

All tools return JSON-serialisable dicts. File artefacts produced by
``boltz_run_comparison`` are written to disk; their paths are returned
in the response so the calling agent can read them.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-BoltZ-Commercial
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from .. import __doi__, __version__

mcp = FastMCP(
    "boltz-kernel",
    instructions=(
        "BoltZ-Kernel: Non-Markovian quantum dynamics solver with Boltzmann "
        "memory kernel. Tools expose the solver for single comparisons, "
        "Prony decomposition, benchmarks, and branding configuration. "
        "All computation runs locally in the BoltZ-Kernel Python process."
    ),
)


# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def boltz_run_comparison(
    spectral: str = "lorentzian",
    omega0: float = 1.0,
    g: float = 1.0,
    T: float = 0.05,
    t_max: float = 50.0,
    dt: float = 0.2,
    backend: str = "auto",
    # Built-in spectral-density tunables
    eta: float = 0.1,
    wc: float = 5.0,
    width: float = 0.5,
    s_ohmic: int = 1,
    beta: float = 0.05,
    we: float = 5.0,
    gap_width: float = 2.0,
    gamma_1d: float = 0.5,
    tau_rt: float = 1.0,
    r: float = 0.9,
    # Prony-specific (backend="prony" only)
    prony_order: Optional[int] = None,
    prony_maxent: bool = False,
    # Output configuration
    output_dir: str = "./boltz_mcp_results",
    visual: str = "svg",       # "svg" | "pdf" | "png" | "tiff" | "eps" | "none"
    raw: str = "csv",          # "csv" | "hdf5" | "parquet" | "none"
    # Branding overrides (optional — persistent branding used if None)
    institute: Optional[str] = None,
    subtitle: Optional[str] = None,
    reference: Optional[str] = None,
    logo_path: Optional[str] = None,
    footer: Optional[str] = None,
) -> dict[str, Any]:
    """
    Run a single Non-Markovian vs Lindblad comparison on a built-in
    spectral density and produce the full artefact set — structured
    metadata (JSON), the rendered comparison figure (SVG/PDF/PNG/TIFF/EPS
    with the persistent or overridden branding applied), and the raw
    time-series (CSV/HDF5/Parquet).

    This is the same output pipeline used by the CLI ``boltz-kernel run``
    and the PyQt6 GUI, so an MCP agent sees identical artefacts.

    Returns a dict with: summary metrics, a ``prony`` sub-block when the
    backend produced one, and ``artifacts`` — the list of paths written.
    """
    import time
    from datetime import datetime, timezone

    from ..branding import BrandingConfig
    from ..core import compare, SpectralDensities
    from ..output import write_all

    backend_kwargs = {}
    if prony_order is not None:
        backend_kwargs["n_exp"] = int(prony_order)
    if prony_maxent:
        backend_kwargs["use_maxent_selector"] = True

    densities = {
        "ohmic": lambda: SpectralDensities.ohmic(eta=eta, wc=wc, s=s_ohmic),
        "super_ohmic": lambda: SpectralDensities.ohmic(eta=eta, wc=wc, s=3),
        "lorentzian": lambda: SpectralDensities.lorentzian(gamma=eta, wc=wc, width=width),
        "band_edge": lambda: SpectralDensities.band_edge(beta=beta, we=we),
        "photonic_crystal": lambda: SpectralDensities.photonic_crystal(
            beta=beta, we=we, gap_width=gap_width),
        "waveguide": lambda: SpectralDensities.waveguide(
            gamma_1d=gamma_1d, tau_rt=tau_rt, r=r),
    }
    if spectral not in densities:
        return {
            "error": f"Unknown spectral density {spectral!r}. "
                     f"Valid: {sorted(densities)}.",
        }
    J = densities[spectral]()

    # Load persistent branding, apply overrides
    branding = BrandingConfig.load()
    if institute is not None:  branding.institute_name = institute
    if subtitle is not None:   branding.subtitle = subtitle
    if reference is not None:  branding.reference = reference
    if logo_path is not None:  branding.logo_path = logo_path
    if footer is not None:     branding.footer_text = footer

    # Solve
    t0 = time.perf_counter()
    cmp = compare(
        J, g=g, T=T, omega0=omega0, t_max=t_max, dt=dt,
        backend=backend, **backend_kwargs,
    )
    wall_time = time.perf_counter() - t0

    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    # Build the canonical run_meta schema — same shape as the CLI's JSON
    run_meta = {
        "schema_version": "1.0",
        "tool": {"name": "BoltZ-Kernel", "version": __version__, "doi": __doi__},
        "run": {
            "id": f"mcp_{int(time.time() * 1000)}",
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "status": "success",
            "source": "mcp_server",
        },
        "input": {
            "spectral": spectral, "g": g, "T": T, "omega0": omega0,
            "t_max": t_max, "dt": dt, "backend": backend,
        },
        "output": {
            "regime_kernel": cmp.regime.lower().replace(" ", "_").replace("-", "_"),
            "metrics": {
                "P_memory": float(cmp.kernel.non_markovianity()),
                "sigma_K": float(cmp.kernel.memory_spread()),
                "max_trace_distance": float(cmp.max_deviation),
                "delta_population_nm": float(
                    abs(cmp.nm.populations[-1] - cmp.nm.populations[0])),
                "delta_population_markov": float(
                    abs(cmp.markov.populations[-1] - cmp.markov.populations[0])),
                "lindblad_valid": bool(cmp.max_deviation < 0.01),
            },
        },
        "execution": {"wall_time_s": round(wall_time, 6)},
        "artifacts": [],
    }
    if getattr(cmp.kernel, "_prony", None) is not None:
        pr = cmp.kernel._prony
        run_meta["output"]["prony"] = {
            "n_exp": int(pr.n_exp),
            "residual": float(pr.residual),
            "variance_explained": float(pr.variance_explained),
        }

    # Write the full artefact set via the shared output pipeline
    # (same function used by CLI run).
    source_label = f"{spectral} (MCP)"
    artifacts = write_all(
        output_dir=out,
        cmp=cmp,
        run_meta=run_meta,
        branding=branding,
        source_label=source_label,
        structured="json",
        visual=visual,
        raw=raw,
    )
    run_meta["artifacts"] = [
        {"type": a["type"], "path": str(out / a["path"])} for a in artifacts
    ]

    # Flattened summary for the agent (plus full run_meta for machine readers)
    return {
        "tool": run_meta["tool"],
        "regime_kernel": run_meta["output"]["regime_kernel"],
        "P_memory": run_meta["output"]["metrics"]["P_memory"],
        "max_trace_distance": run_meta["output"]["metrics"]["max_trace_distance"],
        "lindblad_valid": run_meta["output"]["metrics"]["lindblad_valid"],
        "delta_population_nm": run_meta["output"]["metrics"]["delta_population_nm"],
        "delta_population_markov": run_meta["output"]["metrics"]["delta_population_markov"],
        "wall_time_s": run_meta["execution"]["wall_time_s"],
        "prony": run_meta["output"].get("prony"),
        "input": run_meta["input"],
        "artifacts": run_meta["artifacts"],
        "output_dir": str(out),
    }


@mcp.tool()
def boltz_prony_decompose(
    tau: list[float],
    C_real: list[float],
    C_imag: list[float],
    n_exp: Optional[int] = None,
    use_maxent_selector: bool = False,
    entropy_ratio_threshold: float = 0.95,
) -> dict[str, Any]:
    """
    Matrix-Pencil exponential decomposition of a bath correlation
    function C(τ) = Σₖ αₖ exp(-βₖ τ).

    Inputs: ``tau`` (uniform grid), ``C_real`` and ``C_imag`` samples.

    Returns: alphas (complex → (real, imag) pairs), betas, residual,
    variance_explained, n_exp, top singular values.
    """
    import numpy as np
    from ..core.prony import prony_decompose, maxent_select_order

    tau_arr = np.asarray(tau, dtype=float)
    C_arr = np.asarray(C_real, dtype=float) + 1j * np.asarray(C_imag, dtype=float)

    kwargs: dict[str, Any] = {}
    if n_exp is not None:
        kwargs["n_exp"] = int(n_exp)
    elif use_maxent_selector:
        # Pre-compute SVD to feed MaxEnt selector
        n = len(C_arr)
        L = n // 2
        H = np.array(
            [[C_arr[i + j] for j in range(n - L)] for i in range(L + 1)],
            dtype=complex,
        )
        _, sv, _ = np.linalg.svd(H, full_matrices=False)
        kwargs["n_exp"] = maxent_select_order(
            sv, entropy_ratio_threshold=entropy_ratio_threshold,
        )

    result = prony_decompose(tau_arr, C_arr, **kwargs)
    return {
        "n_exp": int(result.n_exp),
        "alphas": [(float(a.real), float(a.imag)) for a in result.alphas],
        "betas": [(float(b.real), float(b.imag)) for b in result.betas],
        "residual": float(result.residual),
        "variance_explained": float(result.variance_explained),
        "top_singular_values": [
            float(s) for s in result.singular_values[:min(8, len(result.singular_values))]
        ],
        "selection_criterion": (
            "maxent" if use_maxent_selector and n_exp is None
            else ("variance_ratio" if n_exp is None else "manual")
        ),
    }


@mcp.tool()
def boltz_backends_info() -> dict[str, Any]:
    """
    Metadata about available bath-correlation / solver backends.

    Useful for a calling agent to reason about which backend to pick
    before invoking boltz_run_comparison.
    """
    return {
        "auto": {
            "status": "default",
            "routes_to": "fft",
            "notes": "Future versions will detect J structure and route to prony/nufft.",
        },
        "fft": {
            "status": "stable",
            "complexity": "O(N log N)",
            "best_for": "smooth J with fast-decaying tails",
            "verified": "analytical Lorentzian match",
        },
        "quad": {
            "status": "stable (legacy)",
            "complexity": "O(N_τ · prefactor)",
            "best_for": "verification / reference",
            "caveats": "fails convergence on oscillatory integrands at large τ",
        },
        "prony": {
            "status": "stable",
            "complexity": "O(N · K), K≈1-16",
            "best_for": "J with low-order exponential structure",
            "speedup_on_solve": "14-450×",
            "maxent_selector": "opt-in via use_maxent_selector=True",
        },
        "nufft": {
            "status": "Phase C — not yet implemented",
            "planned_for": "J with singularities (band_edge, photonic_crystal gap)",
        },
    }


@mcp.tool()
def boltz_branding_show() -> dict[str, Any]:
    """Show the current persistent branding configuration
    (~/.boltz-kernel/branding.json)."""
    from ..branding import BrandingConfig
    cfg = BrandingConfig.load()
    return {
        "institute_name": cfg.institute_name,
        "subtitle": cfg.subtitle,
        "reference": cfg.reference,
        "logo_path": cfg.logo_path,
        "logo_position": cfg.logo_position,
        "footer_text": cfg.footer_text,
    }


@mcp.tool()
def boltz_branding_set(
    institute_name: Optional[str] = None,
    subtitle: Optional[str] = None,
    reference: Optional[str] = None,
    logo_path: Optional[str] = None,
    logo_position: Optional[str] = None,
    footer_text: Optional[str] = None,
) -> dict[str, Any]:
    """Update one or more persistent branding fields."""
    from ..branding import BrandingConfig
    cfg = BrandingConfig.load()
    if institute_name is not None:  cfg.institute_name = institute_name
    if subtitle is not None:        cfg.subtitle = subtitle
    if reference is not None:       cfg.reference = reference
    if logo_path is not None:       cfg.logo_path = logo_path
    if logo_position is not None:   cfg.logo_position = logo_position
    if footer_text is not None:     cfg.footer_text = footer_text
    cfg.save()
    return boltz_branding_show()


@mcp.tool()
def boltz_version() -> dict[str, str]:
    """Return BoltZ-Kernel version and DOI."""
    return {
        "name": "BoltZ-Kernel",
        "version": __version__,
        "doi": __doi__,
        "mcp_tools": [
            "boltz_run_comparison",
            "boltz_prony_decompose",
            "boltz_backends_info",
            "boltz_branding_show",
            "boltz_branding_set",
            "boltz_version",
        ],
    }


# ── Entry point ───────────────────────────────────────────────────────────────

def launch(transport: str = "stdio", host: str = "127.0.0.1", port: int = 7787) -> int:
    """Launch the MCP server.

    transport: "stdio" (default, for Claude Desktop / Code integration)
               "http"  (streamable HTTP on host:port, for browser-based agents)
    """
    if transport == "stdio":
        mcp.run(transport="stdio")
    elif transport in ("http", "streamable-http"):
        # FastMCP supports streamable HTTP via .run("streamable-http")
        mcp.run(transport="streamable-http", host=host, port=port)
    else:
        raise ValueError(
            f"Unknown MCP transport: {transport!r}. Use 'stdio' or 'http'."
        )
    return 0
