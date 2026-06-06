"""
Unified MCP server for the Metcore (Hope 'n Mind).

This module is the aggregation layer that was previously missing: it exposes
the suite's scientific engines (memkern, obliquity-ng, and - when installed -
boltz-kernel) as a single FastMCP server, so that any MCP client configured by
``hopenmind-mcp configure`` actually has a server to talk to.

Design notes
------------
* Every tool returns a plain JSON-serialisable ``dict`` (never a numpy array),
  so the output is safe across all MCP transports and clients.
* Optional engines are imported lazily and degrade gracefully: if a package is
  not installed, its tools are simply not registered, and ``suite_info`` reports
  which groups are live. The server always starts, even with only memkern.
* Complex numbers cross the wire as ``{"re": ..., "im": ...}`` or as paired
  real/imag lists, because JSON has no native complex type.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-HopenMind-Commercial
Author: DESVAUX G.J.Y. - Hope 'n Mind SASU - Research - contact@hopenmind.com
"""

from __future__ import annotations

import importlib
from typing import Any, Optional

import numpy as np

try:
    from mcp.server.fastmcp import FastMCP
except Exception as exc:  # pragma: no cover - import guard
    raise RuntimeError(
        "The 'mcp' package is required to run the Hope 'n Mind MCP server. "
        "Install it with:  pip install \"hopenmind-mcp[serve]\"  (or  pip install mcp)."
    ) from exc


SERVER_NAME = "metcore"
SERVER_VERSION = "0.1.0"

mcp = FastMCP(
    SERVER_NAME,
    instructions=(
        "Metcore (Hope 'n Mind) - non-Markovian dynamics toolkit. "
        "Compile measured memory kernels into rational/Prony form, embed them as "
        "Markovian dynamics (Markov Embedding Theorem), and diagnose the geometric "
        "non-Markovianity N_G. Start with `suite_info` to see which engines are live."
    ),
)




@mcp.tool()
def kernel_embeddability(
    tau: list[float],
    c_real: list[float],
    c_imag: Optional[list[float]] = None,
) -> dict[str, Any]:
    """Decide whether the Markov Embedding Theorem even applies to C(tau).

    The MET requires a *rational* kernel: a clean rank cliff in the Hankel
    singular spectrum. If the spectrum decays as a power law (no cliff), the
    kernel is sub-ohmic and only the epsilon-extension applies. This tool returns
    the regime ("rational-embeddable" / "borderline" / "power-law/sub-ohmic"),
    the estimated embedding dimension K, the spectral gap, and plain-language
    scope advice. Run it BEFORE trusting any finite-K embedding on measured data.
    """
    from memkern import embeddability_report

    t = np.asarray(tau, dtype=float)
    c = np.asarray(c_real, dtype=float).astype(complex)
    if c_imag is not None:
        c = c + 1j * np.asarray(c_imag, dtype=float)
    if t.size != c.size:
        return {"error": f"length mismatch: tau={t.size}, C={c.size}"}
    try:
        return embeddability_report(t, c)
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}

# ───────────────────────────── capability probe ──────────────────────────────

def _engine_available(module: str) -> bool:
    try:
        importlib.import_module(module)
        return True
    except Exception:
        return False


def _version_of(module: str) -> Optional[str]:
    try:
        return getattr(importlib.import_module(module), "__version__", None)
    except Exception:
        return None


# ────────────────────────────────── tools ────────────────────────────────────

@mcp.tool()
def suite_info() -> dict[str, Any]:
    """Report server version and which scientific engines are currently live.

    Use this first. It tells you which tool groups are available in this
    deployment (memkern / obliquity-ng / boltz-kernel) and their versions.
    """
    engines = {
        "memkern": {
            "available": _engine_available("memkern"),
            "version": _version_of("memkern"),
            "tools": ["prony_decompose", "maxent_select_order", "kernel_embeddability"],
            "role": "MET-Compiler: rational/Prony decomposition of memory kernels.",
        },
        "obliquity_ng": {
            "available": _engine_available("obliquity_ng"),
            "version": _version_of("obliquity_ng"),
            "tools": ["nonmarkovianity_ng"],
            "role": "Geometric non-Markovianity N_G via projective obliquity.",
        },
        "boltz_kernel": {
            "available": _engine_available("boltz_kernel"),
            "version": _version_of("boltz_kernel"),
            "tools": ["boltz_run_comparison", "boltz_prony_decompose"],
            "role": "Open-quantum-systems adapter (optional).",
        },
    }
    return {
        "server": SERVER_NAME,
        "version": SERVER_VERSION,
        "author": "DESVAUX G.J.Y. - Hope 'n Mind SASU - Research",
        "doi": "10.5281/zenodo.20557167",
        "engines": engines,
        "extra_tools": ["lindblad_gap", "cptp_certify", "full_diagnosis", "kernel_zoo",
                        "export_formats", "export_curve", "branding_get", "branding_set",
                        "exterior_lindblad_rate", "kuramoto_critical_coupling",
                        "rf_resonance_shift", "reaction_time_scaling"],
        "live_tools": [t for e in engines.values() if e["available"] for t in e["tools"]],
    }


@mcp.tool()
def prony_decompose(
    tau: list[float],
    c_real: list[float],
    c_imag: Optional[list[float]] = None,
    n_exp: Optional[int] = None,
    max_n_exp: int = 16,
) -> dict[str, Any]:
    """Fit a memory kernel C(τ) ≈ Σₖ αₖ·exp(-βₖ·τ) by Matrix-Pencil/Prony.

    Parameters
    ----------
    tau : uniform time grid starting at 0 (sorted, monotone).
    c_real : real part of the kernel samples C(τ), same length as `tau`.
    c_imag : optional imaginary part (omit for real kernels).
    n_exp : number of exponentials K. If null, chosen automatically from the
        singular spectrum of the Hankel pencil (capped at `max_n_exp`).
    max_n_exp : cap for the auto-selection path.

    Returns the complex amplitudes αₖ and rates βₖ (the Prony modes), the order
    K, and the RMS reconstruction error on the input grid. K equals the optimal
    auxiliary dimension of the Markov embedding (Hankel rank).
    """
    from memkern import prony_decompose as _prony

    t = np.asarray(tau, dtype=float)
    c = np.asarray(c_real, dtype=float).astype(complex)
    if c_imag is not None:
        c = c + 1j * np.asarray(c_imag, dtype=float)
    if t.shape != c.shape:
        return {"error": f"length mismatch: tau={t.size}, C={c.size}"}
    if t.size < 4:
        return {"error": "need at least 4 samples for a meaningful Prony fit"}

    try:
        res = _prony(t, c, n_exp=n_exp, max_n_exp=max_n_exp)
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}

    recon = res.evaluate(t)
    rms = float(np.sqrt(np.mean(np.abs(recon - c) ** 2)))
    return {
        "n_exp": int(res.n_exp),
        "amplitudes": [{"re": float(a.real), "im": float(a.imag)} for a in res.alphas],
        "rates": [{"re": float(b.real), "im": float(b.imag)} for b in res.betas],
        "rms_reconstruction_error": rms,
        "interpretation": (
            f"Kernel compiled into {int(res.n_exp)} exponential mode(s); "
            f"K={int(res.n_exp)} is the extended-space auxiliary dimension of the "
            f"Markov embedding."
        ),
    }


@mcp.tool()
def maxent_select_order(
    singular_values: list[float],
    max_n_exp: int = 16,
    entropy_ratio_threshold: float = 0.95,
) -> dict[str, Any]:
    """Select the Prony order K from a Hankel singular spectrum (MaxEnt criterion).

    This is the suite's novel `maxent_select_order`: given the singular values of
    the Hankel pencil of C(τ), it picks K via a maximum-entropy / effective-number-
    of-modes rule instead of an ad-hoc variance cutoff.
    """
    from memkern import maxent_select_order as _sel

    sv = np.asarray(singular_values, dtype=float)
    if sv.size == 0:
        return {"error": "singular_values is empty"}
    try:
        k = int(_sel(sv, max_n_exp=max_n_exp,
                     entropy_ratio_threshold=entropy_ratio_threshold))
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
    p = sv ** 2 / np.sum(sv ** 2)
    p = p[p > 0]
    n_eff = float(np.exp(-np.sum(p * np.log(p))))
    return {
        "selected_order": k,
        "effective_number_of_modes": n_eff,
        "n_singular_values": int(sv.size),
        "interpretation": f"Recommended Prony order K = {k} (N_eff ≈ {n_eff:.2f}).",
    }


@mcp.tool()
def nonmarkovianity_ng(
    channel: str = "revival",
    gamma: float = 0.1,
    omega: float = 2.0,
    t_max: float = 12.0,
    n_points: int = 2048,
) -> dict[str, Any]:
    """Compute the geometric non-Markovianity N_G of a canonical qubit channel.

    `channel` is one of:
      * "revival"          - non-Markovian oscillating channel (expect N_G > 0).
      * "dephasing"        - Markovian (expect N_G ≈ 0).
      * "depolarizing"     - Markovian (expect N_G ≈ 0).
      * "amplitude_damping"- Markovian (expect N_G ≈ 0).

    `gamma` is the decay rate; `omega` the oscillation frequency (revival only).
    N_G is the integrated positive obliquity of the Bloch-volume flow: 0 for
    CP-divisible (Markovian) dynamics, > 0 when memory makes the volume re-expand.
    """
    import obliquity_ng as ong

    builders = {
        "revival": lambda: ong.nonmarkovian_revival_channel(gamma=gamma, omega=omega),
        "dephasing": lambda: ong.dephasing_channel(gamma),
        "depolarizing": lambda: ong.depolarizing_channel(gamma),
        "amplitude_damping": lambda: ong.amplitude_damping_channel(gamma),
    }
    if channel not in builders:
        return {"error": f"unknown channel {channel!r}; "
                         f"choose from {sorted(builders)}"}
    if n_points < 16:
        return {"error": "n_points too small; use >= 16"}

    try:
        ch = builders[channel]()
        t = np.linspace(0.0, float(t_max), int(n_points))
        M = ch(t)
        ng = float(ong.ng_from_bloch_matrices(M, t))
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}

    markovian = ng < 1e-4
    return {
        "channel": channel,
        "gamma": gamma,
        "omega": omega if channel == "revival" else None,
        "N_G": ng,
        "t_max": t_max,
        "n_points": int(n_points),
        "verdict": "Markovian (CP-divisible)" if markovian
                   else "non-Markovian (memory backflow)",
        "interpretation": (
            f"N_G = {ng:.4g}. " + (
                "Within numerical zero: the dynamics is CP-divisible, i.e. Lindblad "
                "is exact here." if markovian else
                "Strictly positive: the Bloch volume re-expands - Lindblad would "
                "miss exactly this much memory."
            )
        ),
    }



def _to_complex(c_real, c_imag):
    c = np.asarray(c_real, dtype=float).astype(complex)
    if c_imag is not None:
        c = c + 1j * np.asarray(c_imag, dtype=float)
    return c


@mcp.tool()
def lindblad_gap(tau: list[float], c_real: list[float],
                 c_imag: Optional[list[float]] = None,
                 t_max: float = 20.0) -> dict[str, Any]:
    """How wrong is the Lindblad (Markovian) approximation for this kernel?

    Compiles C(tau) to Prony modes, then reports the asymptotic rate gamma_M,
    the peak gap and the time-integrated Lindblad error between the exact and
    Lindblad dephasing coherence. Large integrated_gap => Lindblad badly misses
    the memory.
    """
    from memkern import prony_decompose, embeddability_report, lindblad_gap as _lg
    t = np.asarray(tau, dtype=float); c = _to_complex(c_real, c_imag)
    if t.size != c.size:
        return {"error": f"length mismatch: tau={t.size}, C={c.size}"}
    try:
        K = int(embeddability_report(t, c).get("K_est", 1))
        res = prony_decompose(t, c, n_exp=K)
        out = _lg(res.alphas, res.betas, t_max=t_max)
        for k in ("t", "coherence_exact", "coherence_lindblad", "gap"):
            out.pop(k, None)
        out["K"] = K
        return out
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


@mcp.tool()
def cptp_certify(tau: list[float], c_real: list[float],
                 c_imag: Optional[list[float]] = None,
                 t_max: float = 20.0) -> dict[str, Any]:
    """Certify CP-divisibility (scalar matrix-Bernstein) of the kernel C(tau).

    Returns whether the dephasing dynamics is CP-divisible (Lindblad admissible),
    the most negative time-local rate, and the time windows where CP breaks.
    """
    from memkern import prony_decompose, embeddability_report, cptp_certify as _cc
    t = np.asarray(tau, dtype=float); c = _to_complex(c_real, c_imag)
    if t.size != c.size:
        return {"error": f"length mismatch: tau={t.size}, C={c.size}"}
    try:
        K = int(embeddability_report(t, c).get("K_est", 1))
        res = prony_decompose(t, c, n_exp=K)
        return _cc(res.alphas, res.betas, t_max=t_max)
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


@mcp.tool()
def full_diagnosis(tau: list[float], c_real: list[float],
                   c_imag: Optional[list[float]] = None,
                   t_max: float = 20.0) -> dict[str, Any]:
    """One-call non-Markovian pipeline: embeddability -> Prony -> CP cert -> Lindblad gap.

    The coherence->decoherence bench in a single call. Returns a structured report
    with each step plus a plain-language summary.
    """
    from memkern import full_diagnosis as _fd
    t = np.asarray(tau, dtype=float); c = _to_complex(c_real, c_imag)
    if t.size != c.size:
        return {"error": f"length mismatch: tau={t.size}, C={c.size}"}
    try:
        return _fd(t, c, t_max=t_max)
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


@mcp.tool()
def kernel_zoo(sample: Optional[str] = None, t_max: float = 12.0,
               n_points: int = 256) -> dict[str, Any]:
    """List canonical benchmark kernels, or sample one by name.

    Without `sample`: returns the catalogue. With `sample` (e.g. "drude",
    "underdamped", "maxwell_wiechert", "subohmic"): returns tau and C(tau)
    samples ready to feed the other tools.
    """
    from memkern import zoo
    if sample is None:
        return {"kernels": zoo.list_zoo()}
    try:
        k = zoo.get_kernel(sample)
        t = np.linspace(0.0, float(t_max), int(n_points))
        C = np.asarray(k.C(t), dtype=complex)
        return {"name": k.name, "domain": k.domain, "rational": k.rational,
                "tau": t.tolist(),
                "c_real": np.real(C).tolist(), "c_imag": np.imag(C).tolist()}
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


# ───────────────────────── analytic shortcuts (one stroke) ───────────────────

@mcp.tool()
def exterior_lindblad_rate(alphas_re: list[float], betas_re: list[float],
                           alphas_im: Optional[list[float]] = None,
                           betas_im: Optional[list[float]] = None) -> dict[str, Any]:
    """Asymptotic Markovian rate gamma_M in ONE STROKE from Prony data.

    gamma_M = Re sum_k alpha_k/beta_k. Replaces integrating the full
    Nakajima-Zwanzig dynamics to t->infinity and extracting the time-local
    generator (minutes of ODE work) by a single algebraic sum (<1 ms).
    """
    from memkern.shortcuts import exterior_rate
    a = np.asarray(alphas_re, float).astype(complex)
    b = np.asarray(betas_re, float).astype(complex)
    if alphas_im is not None:
        a = a + 1j * np.asarray(alphas_im, float)
    if betas_im is not None:
        b = b + 1j * np.asarray(betas_im, float)
    try:
        return exterior_rate(a, b)
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


@mcp.tool()
def kuramoto_critical_coupling(alphas: list[float], betas: list[float],
                               gamma_g: float = 0.5) -> dict[str, Any]:
    """Synchronization threshold of Kuramoto WITH memory, in ONE STROKE.

    K_c(M) = 2*gamma_g / M_hat(0), with M_hat(0) = sum_k alpha_k/beta_k
    (paper2, Eq. 6; Lorentzian frequency spread of half-width gamma_g).
    Replaces a K-sweep of the retarded Kuramoto model plus transition
    fitting (typically 10+ minutes per system) by one formula evaluation.
    """
    from memkern.shortcuts import kuramoto_kc
    try:
        return kuramoto_kc(alphas, betas, gamma_g=gamma_g)
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


@mcp.tool()
def rf_resonance_shift(A: float, omega_p: float, omega0: float,
                       gamma0: float, m_base0: float = 1.0) -> dict[str, Any]:
    """Threshold shift under a periodic perturbation, in ONE STROKE.

    Lorentzian line shape (paper3a, Prop. 2): dKc/Kc =
    (A/w_p^2)/(M0 - A/w_p^2) * gamma0^2/((w_p-w0)^2+gamma0^2).
    Replaces re-running the full threshold sweep at every perturbation
    frequency by an O(1) evaluation per frequency.
    """
    from memkern.shortcuts import rf_resonance_shift as _rf
    try:
        return _rf(A=A, omega_p=omega_p, omega0=omega0,
                   gamma0=gamma0, m_base0=m_base0)
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


@mcp.tool()
def reaction_time_scaling(tau_l: float, tau_d: float, theta: float,
                          i0: float) -> dict[str, Any]:
    """Mean reaction time from kernel parameters, in ONE STROKE.

    <RT> = tau_l + tau_d * ln(theta/I0), sigma_RT ~ tau_d (paper3a, Cor. 1).
    Replaces a behavioral 2AFC campaign plus inverse-Gaussian fitting when
    only the scaling is needed.
    """
    from memkern.shortcuts import rt_scaling
    try:
        return rt_scaling(tau_l=tau_l, tau_d=tau_d, theta=theta, i0=i0)
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


# ───────────────────────── branding over MCP ─────────────────────────────────

@mcp.tool()
def branding_get() -> dict[str, Any]:
    """Read the branding/theme applied to every rendered figure and table.

    Convention: the returned keys mirror ~/.metcore/branding.json - the SAME
    file the desktop GUI edits, so changes made here show up in the app and
    vice versa. logo_path has three states: "auto" = the bundled "Your logo
    here" placeholder, "" = no logo, any other value = path to a custom logo.
    theme_presets lists named (primary, secondary) color pairs accepted by
    branding_set's pseudo-key "theme_preset".
    """
    try:
        from dataclasses import asdict
        from metcore_export import BrandingConfig, THEME_PRESETS
    except Exception as exc:
        return {"error": f"metcore-export not installed: {exc}"}
    return {
        "branding": asdict(BrandingConfig.load()),
        "theme_presets": {k: list(v) for k, v in THEME_PRESETS.items()},
        "logo_path_convention": {
            "auto": "bundled 'Your logo here' placeholder",
            "": "no logo",
            "<path>": "custom logo image on this machine",
        },
    }


@mcp.tool()
def branding_set(changes: dict[str, str]) -> dict[str, Any]:
    """Apply branding/theme changes; they persist and affect every next render.

    Accepted keys (same as branding_get): institute_name, subtitle, reference,
    logo_path ("auto" / "" / path), logo_position ("left"/"right"),
    footer_text, source_label, theme_primary, theme_secondary (hex colors).
    Pseudo-key "theme_preset": a name from branding_get()["theme_presets"],
    expanded into both theme colors. Unknown keys are reported, not applied.
    Typical flow: branding_get -> show the user a proposal -> branding_set.
    """
    try:
        from dataclasses import asdict
        from metcore_export import BrandingConfig, THEME_PRESETS
    except Exception as exc:
        return {"error": f"metcore-export not installed: {exc}"}
    cfg = BrandingConfig.load()
    allowed = set(asdict(cfg)) - {"embed_hnm_metadata"}
    applied: dict[str, str] = {}
    rejected: dict[str, str] = {}
    ch = dict(changes or {})
    preset = ch.pop("theme_preset", None)
    if preset is not None:
        if preset in THEME_PRESETS:
            cfg.theme_primary, cfg.theme_secondary = THEME_PRESETS[preset]
            applied["theme_preset"] = preset
        else:
            rejected["theme_preset"] = f"unknown; choose from {sorted(THEME_PRESETS)}"
    for k, v in ch.items():
        if k in allowed:
            setattr(cfg, k, str(v))
            applied[k] = str(v)
        else:
            rejected[k] = "unknown key"
    if applied:
        cfg.save()
    return {"applied": applied, "rejected": rejected,
            "branding": asdict(cfg),
            "note": "Persisted to ~/.metcore/branding.json; every next render "
                    "(GUI, exports, export_curve) uses it."}


# ───────────────────────── file-producing exports ────────────────────────────

@mcp.tool()
def export_formats() -> dict[str, Any]:
    """List every output `export_curve` can write to disk.

    Returns the seven academic image formats (PNG 300/600, PDF, SVG, EPS,
    TIFF 300/600) and the data attachments (XML sidecar, CSV, Excel, and an
    "image with an embedded value table" PNG). Pass any of these keys in
    `export_curve(outputs=[...])`.
    """
    try:
        from metcore_export import ACADEMIC_FORMATS, ATTACHMENTS
    except Exception as exc:
        return {"error": f"metcore-export not installed: {exc}"}
    return {
        "image_formats": [{"key": k, "ext": e, "dpi": d} for k, e, d in ACADEMIC_FORMATS],
        "data_attachments": [{"key": a.key, "label": a.label} for a in ATTACHMENTS],
        "note": ("Image-format keys write the figure; csv / xlsx / xml / image_table "
                 "write the numbers. Use export_curve to emit any subset."),
    }


@mcp.tool()
def export_curve(columns: dict[str, list[float]], outdir: str, basename: str,
                 outputs: Optional[list[str]] = None,
                 title: Optional[str] = None) -> dict[str, Any]:
    """Write a curve (named columns) to disk in chosen formats.

    Parameters
    ----------
    columns : ordered map {name: values}. The FIRST column is the x-axis; the
        rest are plotted as y-series (e.g. {"t": [...], "V(t)": [...]}).
    outdir : destination folder on the machine running this server (created if
        needed).
    basename : stem for every written file.
    outputs : list of keys from `export_formats` (default: ["csv"]). Mix image
        formats (png600, pdf, svg, ...) with data attachments (csv, xlsx, xml,
        image_table).
    title : optional figure title for the image outputs.

    Returns the absolute output folder and a map of written paths per key.
    """
    import os
    try:
        from metcore_export import (
            ACADEMIC_FORMATS, BrandingConfig, apply_branding, export_all,
            export_csv, export_xlsx, export_xml, write_attachment)
    except Exception as exc:
        return {"error": f"metcore-export not installed: {exc}"}

    if not columns:
        return {"error": "columns is empty"}
    series = [(str(k), np.asarray(v, dtype=float).ravel()) for k, v in columns.items()]
    keys = list(outputs) if outputs else ["csv"]
    img_keys = {k for k, _, _ in ACADEMIC_FORMATS}

    def make_fig():
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        fig = Figure(figsize=(7.5, 4.6)); FigureCanvasAgg(fig)
        ax = fig.add_axes([0.12, 0.13, 0.80, 0.66])
        x = series[0][1]
        from metcore_export import theme_colors
        th = theme_colors(None)  # saved branding theme
        palette = [th["primary"], th["secondary"]]
        for i, (name, arr) in enumerate(series[1:]):
            ax.plot(x, arr[:len(x)], label=name,
                    color=palette[i] if i < len(palette) else None)
        ax.set_xlabel(series[0][0]); ax.grid(True, alpha=0.25)
        if len(series) > 2:
            ax.legend(fontsize=8)
        if title:
            ax.set_title(title, fontsize=10, pad=8)
        apply_branding(fig, BrandingConfig.load())
        return fig

    written: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for key in keys:
        try:
            if key in img_keys:
                res = export_all(make_fig(), outdir, basename,
                                 formats=[key], apply=False)
                written[key] = [str(p) for p in res.paths()]
            elif key == "csv":
                written[key] = str(export_csv(series, outdir, basename))
            elif key == "xlsx":
                written[key] = str(export_xlsx(series, outdir, basename))
            elif key == "xml":
                written[key] = str(export_xml(dict(columns), outdir, basename))
            elif key == "image_table":
                written[key] = str(write_attachment(
                    "image_table", outdir=outdir, basename=basename,
                    series=series, make_figure=make_fig))
            else:
                errors[key] = "unknown output key (see export_formats)"
        except Exception as exc:  # noqa: BLE001
            errors[key] = f"{type(exc).__name__}: {exc}"
    return {"outdir": os.path.abspath(outdir), "written": written, "errors": errors}


# ───────────────────────── optional boltz-kernel mount ───────────────────────

def _mount_optional_engines() -> list[str]:
    """Register tools from optional engines if importable. Returns mounted names."""
    mounted: list[str] = []
    try:
        bk = importlib.import_module("boltz_kernel.mcp.server")
        # boltz ships its own FastMCP instance `mcp` with @tool functions; re-wrap
        # the plain callables so they live under this unified server too.
        for name in ("boltz_run_comparison", "boltz_prony_decompose",
                     "boltz_backends_info", "boltz_version"):
            fn = getattr(bk, name, None)
            if callable(fn):
                mcp.add_tool(fn)
                mounted.append(name)
    except Exception:
        pass
    return mounted


# ───────────────────────────────── launch ────────────────────────────────────

def launch(transport: str = "stdio", host: str = "127.0.0.1",
           port: int = 8787) -> int:
    """Start the unified MCP server.

    transport: "stdio" (default, for desktop clients) or "http" (streamable HTTP).
    """
    _mount_optional_engines()
    if transport == "http":
        mcp.settings.host = host
        mcp.settings.port = port
        mcp.run("streamable-http")
    else:
        mcp.run("stdio")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(launch())
