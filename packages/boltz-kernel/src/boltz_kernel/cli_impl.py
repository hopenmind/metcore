"""
Orchestration of the `run` subcommand.

Kept separate from cli.py so that typer's --help / version stays instant
(no heavy imports) and so that other entry points (batch, wizard) can reuse
the same helpers.

SPDX-License-Identifier: Apache-2.0 OR LicenseRef-BoltZ-Commercial
"""

from __future__ import annotations

import csv as _csv
import io
import json as _json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import numpy as np

from . import __version__, output
from .branding import BrandingConfig
from .core import SpectralDensities, compare


class InputError(ValueError):
    """Raised for malformed user input (CSV, formula, stdin)."""


# ── J(ω) source resolution ─────────────────────────────────────────────────────

def _resolve_source(
    *,
    spectral: Optional[str],
    csv_file: Optional[Path],
    formula: Optional[str],
    stdin: bool,
    eta: float, wc: float, width: float, s_ohmic: int,
    beta: float, we: float, gap_width: float,
    gamma_1d: float, tau_rt: float, r: float,
) -> tuple[Callable[[float], float], str]:
    """Return (J_callable, human_readable_label). Raises InputError on failure."""
    sources_given = sum(x is not None for x in (spectral, csv_file, formula)) + int(stdin)
    if sources_given == 0:
        # Default: lorentzian cavity (sane baseline)
        spectral = "lorentzian"
    elif sources_given > 1:
        raise InputError(
            "Specify exactly one source: --spectral, --csv, --formula, or --stdin."
        )

    if spectral is not None:
        return _builtin(spectral, eta, wc, width, s_ohmic, beta, we, gap_width,
                        gamma_1d, tau_rt, r)

    if csv_file is not None:
        return _from_csv(csv_file), f"CSV: {csv_file.name}"

    if stdin:
        data = sys.stdin.read()
        return _from_csv_text(data), "CSV (stdin)"

    if formula is not None:
        return _from_formula(formula), f"formula: {formula}"

    raise InputError("No spectral-density source could be resolved.")  # unreachable


def _builtin(name, eta, wc, width, s_ohmic, beta, we, gap_width,
             gamma_1d, tau_rt, r):
    if name == "ohmic":
        J = SpectralDensities.ohmic(eta=eta, wc=wc, s=s_ohmic)
        return J, f"Ohmic(η={eta}, ωc={wc}, s={s_ohmic})"
    if name == "super_ohmic":
        J = SpectralDensities.ohmic(eta=eta, wc=wc, s=3)
        return J, f"Super-Ohmic(η={eta}, ωc={wc}, s=3)"
    if name == "lorentzian":
        J = SpectralDensities.lorentzian(gamma=eta, wc=wc, width=width)
        return J, f"Lorentzian(γ={eta}, ωc={wc}, Δ={width})"
    if name == "band_edge":
        J = SpectralDensities.band_edge(beta=beta, we=we)
        return J, f"BandEdge(β={beta}, ωe={we})"
    if name == "photonic_crystal":
        J = SpectralDensities.photonic_crystal(beta=beta, we=we, gap_width=gap_width)
        return J, f"PhC(β={beta}, ωe={we}, gap={gap_width})"
    if name == "waveguide":
        J = SpectralDensities.waveguide(gamma_1d=gamma_1d, tau_rt=tau_rt, r=r)
        return J, f"Waveguide(Γ_1D={gamma_1d}, τ_rt={tau_rt}, r={r})"
    raise InputError(f"Unknown spectral density: {name}")


def _from_csv(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return _from_csv_text(f.read())


def _from_csv_text(text: str):
    omegas: list[float] = []
    Js: list[float] = []
    reader = _csv.reader(io.StringIO(text))
    for i, row in enumerate(reader):
        if not row or not row[0].strip():
            continue
        # Skip header row if the first cell isn't numeric
        if i == 0:
            try:
                float(row[0])
            except ValueError:
                continue
        # Support comma, tab, or space separation (csv.reader handles comma/tab;
        # if line has only one cell but contains spaces, split manually)
        if len(row) < 2 and " " in row[0]:
            parts = row[0].split()
        else:
            parts = [c.strip() for c in row]
        if len(parts) < 2:
            continue
        try:
            omegas.append(float(parts[0]))
            Js.append(float(parts[1]))
        except ValueError as exc:
            raise InputError(f"Line {i + 1}: cannot parse '{row}' ({exc})") from exc

    if len(omegas) < 2:
        raise InputError("CSV must contain at least 2 data points (omega, J).")
    if any(v < 0 for v in Js):
        raise InputError("J(ω) contains negative values — unphysical spectral density.")

    omegas_arr = np.asarray(omegas)
    Js_arr = np.asarray(Js)
    sort_idx = np.argsort(omegas_arr)
    omegas_arr = omegas_arr[sort_idx]
    Js_arr = Js_arr[sort_idx]

    def J(w: float) -> float:
        if w <= omegas_arr[0] or w >= omegas_arr[-1]:
            return 0.0
        return float(np.interp(w, omegas_arr, Js_arr))

    return J


def _from_formula(expr: str):
    # Restricted eval: numpy + math only, no builtins
    allowed_globals = {
        "__builtins__": {},
        "np": np,
        "numpy": np,
    }
    math_names = ("sin", "cos", "tan", "exp", "log", "sqrt", "pi", "e", "abs")
    for name in math_names:
        allowed_globals[name] = getattr(np, name, None)

    # Validate once by trying a harmless value
    try:
        _ = eval(expr, allowed_globals, {"w": 1.0})
    except Exception as exc:
        raise InputError(f"Invalid formula: {exc}") from exc

    def J(w: float) -> float:
        try:
            v = eval(expr, allowed_globals, {"w": float(w)})
        except Exception:
            return 0.0
        return float(v) if v is not None and np.isfinite(v) else 0.0

    return J


# ── Summary printers ───────────────────────────────────────────────────────────

def _regime_slug(label: str) -> str:
    return {
        "Markovian": "markovian",
        "Weakly non-Markovian": "weakly_non_markovian",
        "Strongly non-Markovian": "strongly_non_markovian",
    }.get(label, label.lower().replace(" ", "_"))


def _print_summary(cmp, run_meta, plain: bool, source_label: str) -> None:
    if plain:
        _print_summary_plain(cmp, run_meta, source_label)
        return
    try:
        from rich.console import Console
        from rich.table import Table
    except ImportError:
        _print_summary_plain(cmp, run_meta, source_label)
        return

    console = Console()
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(justify="right", style="dim")
    table.add_column()

    metrics = run_meta["output"]["metrics"]
    table.add_row("Source", source_label)
    table.add_row("Kernel regime",     cmp.regime + "  (structural, from P)")
    table.add_row("P (memory)",        f"{metrics['P_memory']:.4f}")
    table.add_row("σ_K (spread)",      f"{metrics['sigma_K']:.4f}")
    table.add_row("Δ P_e (NM)",        f"{metrics['delta_population_nm']:.4f}")
    table.add_row("Δ P_e (Markov)",    f"{metrics['delta_population_markov']:.4f}")
    table.add_row("Max trace distance", f"{metrics['max_trace_distance']:.4f}")
    table.add_row("Lindblad valid",    "yes" if metrics["lindblad_valid"] else "no")
    table.add_row("Wall time",         f"{run_meta['execution']['wall_time_s']:.3f} s")
    console.print(table)

    for w in run_meta.get("warnings", []):
        console.print(f"[yellow]Warning ({w['code']}):[/yellow] {w['message']}")

    if run_meta["artifacts"]:
        console.print("[dim]Artefacts:[/dim]")
        for a in run_meta["artifacts"]:
            console.print(f"  {a['type']:12s}  {a['path']}")


def _print_summary_plain(cmp, run_meta, source_label: str) -> None:
    metrics = run_meta["output"]["metrics"]
    sys.stdout.write(
        f"source={source_label}\n"
        f"kernel_regime={cmp.regime}\n"
        f"P_memory={metrics['P_memory']:.4f}\n"
        f"sigma_K={metrics['sigma_K']:.4f}\n"
        f"delta_pop_nm={metrics['delta_population_nm']:.4f}\n"
        f"delta_pop_markov={metrics['delta_population_markov']:.4f}\n"
        f"max_trace_distance={metrics['max_trace_distance']:.4f}\n"
        f"lindblad_valid={'yes' if metrics['lindblad_valid'] else 'no'}\n"
        f"trivial_dynamics={'yes' if metrics['trivial_dynamics'] else 'no'}\n"
        f"wall_time_s={run_meta['execution']['wall_time_s']:.3f}\n"
    )
    for w in run_meta.get("warnings", []):
        sys.stdout.write(f"warning={w['code']}:{w['message']}\n")
    for a in run_meta["artifacts"]:
        sys.stdout.write(f"artifact:{a['type']}={a['path']}\n")


def _error(msg: str, plain: bool) -> None:
    if plain:
        sys.stderr.write(f"ERROR: {msg}\n")
        return
    try:
        from rich.console import Console
        Console(stderr=True).print(f"[red]Error:[/red] {msg}")
    except ImportError:
        sys.stderr.write(f"ERROR: {msg}\n")


# ── Main entry point ───────────────────────────────────────────────────────────

def run_command(
    *,
    spectral, csv_file, formula, stdin,
    g, T, omega0, t_max, dt,
    eta, wc, width, s_ohmic,
    beta, we, gap_width,
    gamma_1d, tau_rt, r,
    output_dir,
    structured, visual, raw,
    institute, subtitle, reference, logo, footer,
    as_json, quiet, plain,
    backend="auto",
    prony_order=None,
    prony_maxent=False,
) -> int:
    """Returns exit code. 0=valid, 1=invalid (publishable), 2=input, 3=internal."""
    try:
        J, source_label = _resolve_source(
            spectral=spectral, csv_file=csv_file, formula=formula, stdin=stdin,
            eta=eta, wc=wc, width=width, s_ohmic=s_ohmic,
            beta=beta, we=we, gap_width=gap_width,
            gamma_1d=gamma_1d, tau_rt=tau_rt, r=r,
        )
    except InputError as exc:
        _error(str(exc), plain=plain)
        return 2

    # Apply branding overrides
    branding = BrandingConfig.load()
    if institute is not None: branding.institute_name = institute
    if subtitle  is not None: branding.subtitle       = subtitle
    if reference is not None: branding.reference      = reference
    if logo      is not None: branding.logo_path      = str(logo)
    if footer    is not None: branding.footer_text    = footer

    # Backend-specific kwargs forwarded to from_spectral_density via compare()
    backend_kwargs = {}
    if prony_order is not None:
        backend_kwargs["n_exp"] = int(prony_order)
    if prony_maxent:
        backend_kwargs["use_maxent_selector"] = True

    # Solve
    t0 = time.perf_counter()
    try:
        cmp = compare(
            J, g=g, T=T, omega0=omega0, t_max=t_max, dt=dt,
            backend=backend, **backend_kwargs,
        )
    except Exception as exc:  # pragma: no cover
        _error(f"Solver error: {exc}", plain=plain)
        return 3
    wall_time = time.perf_counter() - t0

    # Observable-dynamics metrics: how much actually happened
    delta_pop_nm = float(abs(cmp.nm.populations[-1] - cmp.nm.populations[0]))
    delta_pop_mk = float(abs(cmp.markov.populations[-1] - cmp.markov.populations[0]))
    trivial_dynamics = max(delta_pop_nm, delta_pop_mk) < 0.01

    # Metadata dict (canonical schema)
    run_meta = {
        "schema_version": "1.0",
        "tool": {
            "name": "BoltZ-Kernel",
            "version": __version__,
            "doi": "10.5281/zenodo.19648837",
        },
        "run": {
            "id": f"run_{int(time.time() * 1000)}",
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "status": "success",
        },
        "input": {
            "source": source_label,
            "params": {
                "g": g, "T": T, "omega0": omega0,
                "t_max": t_max, "dt": dt,
            },
        },
        "output": {
            "regime_kernel": _regime_slug(cmp.regime),
            "metrics": {
                # Structural (kernel-level) — what the MEMORY looks like
                "P_memory": float(cmp.kernel.non_markovianity()),
                "sigma_K": float(cmp.kernel.memory_spread()),
                # Observable (dynamical) — what the STATE actually does
                "delta_population_nm":     delta_pop_nm,
                "delta_population_markov": delta_pop_mk,
                "max_trace_distance":      float(cmp.max_deviation),
                # Decision
                "lindblad_valid": bool(cmp.max_deviation < 0.01),
                "trivial_dynamics": trivial_dynamics,
            },
        },
        "warnings": [],
        "execution": {
            "wall_time_s": round(wall_time, 6),
        },
        "artifacts": [],
    }

    if trivial_dynamics:
        run_meta["warnings"].append({
            "code": "trivial_dynamics",
            "message": (
                "Excited-state population changed by less than 1% over t_max — "
                "the system is barely evolving. The 'lindblad_valid' conclusion "
                "is dominated by trivial agreement (both solvers describe "
                "'nothing happens'). Likely cause: J(omega0) is very small or "
                "the coupling g is too weak to drive observable dynamics on this "
                "timescale. Increase g, extend t_max, or tune omega0 to a peak "
                "of J(omega)."
            ),
        })

    # Write artefacts in all requested formats
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        artifacts = output.write_all(
            output_dir=output_dir,
            cmp=cmp,
            run_meta=run_meta,
            branding=branding,
            source_label=source_label,
            structured=structured,
            visual=visual,
            raw=raw,
        )
    except Exception as exc:  # pragma: no cover
        _error(f"Output error: {exc}", plain=plain)
        return 3
    run_meta["artifacts"] = artifacts

    # Console / pipeline output
    if as_json:
        payload = {
            "regime_kernel": run_meta["output"]["regime_kernel"],
            "P_memory": run_meta["output"]["metrics"]["P_memory"],
            "max_trace_distance": run_meta["output"]["metrics"]["max_trace_distance"],
            "delta_population_nm": run_meta["output"]["metrics"]["delta_population_nm"],
            "delta_population_markov": run_meta["output"]["metrics"]["delta_population_markov"],
            "lindblad_valid": run_meta["output"]["metrics"]["lindblad_valid"],
            "trivial_dynamics": run_meta["output"]["metrics"]["trivial_dynamics"],
            "warnings": [w["code"] for w in run_meta.get("warnings", [])],
            "files": [a["path"] for a in artifacts],
        }
        sys.stdout.write(_json.dumps(payload) + "\n")
    elif not quiet:
        _print_summary(cmp, run_meta, plain=plain, source_label=source_label)

    return 0 if run_meta["output"]["metrics"]["lindblad_valid"] else 1
